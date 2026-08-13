"""Project-scoped capability execution API.

Selection, consent and execution are deliberately separate:
- selection chooses an available semantic offer;
- preparation reports locality/cost facts and required acknowledgements;
- authorization issues only a short-lived one-shot grant for the exact input;
- execution consumes that grant before any non-local or non-free adapter may run.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.mcp import get_mcp_manager
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities.adapters import (
    LocalFFmpegAdapter,
    NativeVideoClawAdapter,
    WhisperCppAdapter,
)
from uv_studio.capabilities.adapters.argos_translate import ArgosTranslateAdapter
from uv_studio.capabilities.adapters.mcp_execution import (
    MCPExecutionAdapter,
    MCPExecutionInputRejected,
)
from uv_studio.capabilities.adapters.whisperx_alignment import WhisperXAlignmentAdapter
from uv_studio.capabilities.authorization import (
    ConsentScope,
    ExecutionAuthorizationInvalid,
    ExecutionConsentRequired,
    InvalidExecutionInput,
    OneShotAuthorizationStore,
    prepare_execution,
)
from uv_studio.capabilities.execution import (
    CapabilityExecutionEnvelope,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import (
    NoEligibleOffer,
    OfferSelectionDecision,
    OfferSelectionError,
    OfferSelectionRequired,
    PinnedOfferRejected,
    SelectionPolicy,
    select_offer,
)
from uv_studio.mcp.client import (
    MCPCallError,
    MCPCallTimeout,
    MCPRequestTooLarge,
    MCPResponseTooLarge,
    MCPToolReturnedError,
)
from uv_studio.mcp.manager import MCPBindingExecutionRejected, MCPManager
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Capability Execution"])


def get_local_ffmpeg_adapter(
    store: ProjectStore = Depends(get_project_store),
) -> LocalFFmpegAdapter:
    return LocalFFmpegAdapter(store)


def get_whisper_cpp_adapter(
    store: ProjectStore = Depends(get_project_store),
) -> WhisperCppAdapter:
    return WhisperCppAdapter(store)


def get_argos_translate_adapter(
    store: ProjectStore = Depends(get_project_store),
) -> ArgosTranslateAdapter:
    return ArgosTranslateAdapter(store)


def get_whisperx_alignment_adapter(
    store: ProjectStore = Depends(get_project_store),
) -> WhisperXAlignmentAdapter:
    return WhisperXAlignmentAdapter(store)


def get_native_videoclaw_adapter(
    store: ProjectStore = Depends(get_project_store),
) -> NativeVideoClawAdapter:
    return NativeVideoClawAdapter(store)


def get_mcp_execution_adapter(
    store: ProjectStore = Depends(get_project_store),
    manager: MCPManager = Depends(get_mcp_manager),
) -> MCPExecutionAdapter:
    return MCPExecutionAdapter(manager, store)


@lru_cache(maxsize=1)
def get_execution_authorization_store() -> OneShotAuthorizationStore:
    return OneShotAuthorizationStore()


def _selection_policy(value: Any) -> SelectionPolicy:
    if value is None:
        return SelectionPolicy.LOCAL_FREE_FIRST
    try:
        return SelectionPolicy(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="selection_policy must be manual, pinned_offer, or local_free_first",
        ) from exc


def _validate_request(
    request: dict[str, Any],
    *,
    allow_authorization_token: bool = False,
    allow_acknowledgements: bool = False,
) -> tuple[SelectionPolicy, str | None, dict[str, Any]]:
    if not isinstance(request, Mapping):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="request body must be a JSON object",
        )
    allowed = {"selection_policy", "offer_id", "input"}
    if allow_authorization_token:
        allowed.add("authorization_token")
    if allow_acknowledgements:
        allowed.add("acknowledgements")
    unknown_fields = set(request).difference(allowed)
    if unknown_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unsupported execution request fields: {sorted(unknown_fields)!r}",
        )

    policy = _selection_policy(request.get("selection_policy"))
    offer_id = request.get("offer_id")
    if offer_id is not None and not isinstance(offer_id, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="offer_id must be a string when provided",
        )
    input_payload = request.get("input", {})
    if not isinstance(input_payload, Mapping):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="input must be a JSON object",
        )
    return policy, offer_id, dict(input_payload)


def _load_project(store: ProjectStore, project_id: str) -> None:
    try:
        store.load_project(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _select(
    registry: CapabilityRegistry,
    capability_id: str,
    *,
    policy: SelectionPolicy,
    offer_id: str | None,
) -> OfferSelectionDecision:
    try:
        decision = select_offer(
            registry,
            capability_id,
            policy=policy,
            pinned_offer_id=offer_id,
        )
    except UnknownCapability as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability not found",
        ) from exc
    except OfferSelectionRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "manual_selection_required",
                "message": str(exc),
                "offers": [offer.to_dict() for offer in registry.offers_for(capability_id)],
            },
        ) from exc
    except (NoEligibleOffer, PinnedOfferRejected, OfferSelectionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "offer_not_executable", "message": str(exc)},
        ) from exc
    if decision.offer is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="selection policy did not produce an executable offer",
        )
    return decision


def _prepare(
    *,
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore,
    registry: CapabilityRegistry,
    allow_authorization_token: bool = False,
    allow_acknowledgements: bool = False,
):
    policy, offer_id, input_payload = _validate_request(
        request,
        allow_authorization_token=allow_authorization_token,
        allow_acknowledgements=allow_acknowledgements,
    )
    _load_project(store, project_id)
    decision = _select(registry, capability_id, policy=policy, offer_id=offer_id)
    try:
        preparation = prepare_execution(
            project_id=project_id,
            offer=decision.offer,
            selection_policy=policy,
            payload=input_payload,
        )
    except InvalidExecutionInput as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return decision, preparation, input_payload


def _acknowledgements(value: Any) -> set[ConsentScope]:
    if value is None:
        return set()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="acknowledgements must be an array of consent scope strings",
        )
    try:
        result = {ConsentScope(item) for item in value}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "acknowledgements may contain only remote_execution, external_cost, "
                "or unknown_cost"
            ),
        ) from exc
    if len(result) != len(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="acknowledgements must not contain duplicates",
        )
    return result


def _consent_required_detail(preparation) -> dict[str, Any]:
    return {
        "code": "consent_required",
        "message": "selected offer requires explicit one-shot execution authorization",
        "authorization": preparation.to_dict(),
    }


def _mcp_error(exc: Exception, *, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": getattr(exc, "code", "mcp_execution_failed"),
            "message": str(exc),
        },
    )


@router.post("/{project_id}/capabilities/{capability_id}/prepare-execution")
def prepare_project_capability_execution(
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
) -> dict[str, Any]:
    decision, preparation, _ = _prepare(
        project_id=project_id,
        capability_id=capability_id,
        request=request,
        store=store,
        registry=registry,
    )
    return {
        "selection": decision.to_dict(),
        "authorization": preparation.to_dict(),
    }


@router.post("/{project_id}/capabilities/{capability_id}/authorize-execution")
def authorize_project_capability_execution(
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    authorizations: OneShotAuthorizationStore = Depends(get_execution_authorization_store),
) -> dict[str, Any]:
    decision, preparation, _ = _prepare(
        project_id=project_id,
        capability_id=capability_id,
        request=request,
        store=store,
        registry=registry,
        allow_acknowledgements=True,
    )
    acknowledgements = _acknowledgements(request.get("acknowledgements"))
    try:
        token, expires_at = authorizations.issue(
            preparation,
            acknowledgements=acknowledgements,
        )
    except ExecutionConsentRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "acknowledgement_required",
                "message": str(exc),
                "authorization": preparation.to_dict(),
            },
        ) from exc
    return {
        "selection": decision.to_dict(),
        "authorization": preparation.to_dict(),
        "authorization_token": token,
        "expires_at_unix": expires_at,
    }


@router.post("/{project_id}/capabilities/{capability_id}/execute")
async def execute_project_capability(
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    local_ffmpeg: LocalFFmpegAdapter = Depends(get_local_ffmpeg_adapter),
    local_whisper_cpp: WhisperCppAdapter = Depends(get_whisper_cpp_adapter),
    local_argos_translate: ArgosTranslateAdapter = Depends(get_argos_translate_adapter),
    local_whisperx_alignment: WhisperXAlignmentAdapter = Depends(get_whisperx_alignment_adapter),
    native_videoclaw: NativeVideoClawAdapter = Depends(get_native_videoclaw_adapter),
    mcp_execution: MCPExecutionAdapter = Depends(get_mcp_execution_adapter),
    authorizations: OneShotAuthorizationStore = Depends(get_execution_authorization_store),
) -> dict[str, Any]:
    decision, preparation, input_payload = _prepare(
        project_id=project_id,
        capability_id=capability_id,
        request=request,
        store=store,
        registry=registry,
        allow_authorization_token=True,
    )
    token = request.get("authorization_token")
    if token is not None and not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="authorization_token must be a string when provided",
        )
    try:
        authorizations.consume(token, preparation)
    except ExecutionConsentRequired as exc:
        detail = _consent_required_detail(preparation)
        detail["message"] = str(exc)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    except ExecutionAuthorizationInvalid as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "authorization_invalid", "message": str(exc)},
        ) from exc

    offer = decision.offer
    try:
        if offer.adapter_id == LocalFFmpegAdapter.adapter_id:
            result = await run_in_threadpool(
                local_ffmpeg.execute,
                project_id=project_id,
                offer=offer,
                payload=input_payload,
            )
        elif offer.adapter_id == WhisperCppAdapter.adapter_id:
            result = await run_in_threadpool(
                local_whisper_cpp.execute,
                project_id=project_id,
                offer=offer,
                payload=input_payload,
            )
        elif offer.adapter_id == ArgosTranslateAdapter.adapter_id:
            result = await run_in_threadpool(
                local_argos_translate.execute,
                project_id=project_id,
                offer=offer,
                payload=input_payload,
            )
        elif offer.adapter_id == WhisperXAlignmentAdapter.adapter_id:
            result = await run_in_threadpool(
                local_whisperx_alignment.execute,
                project_id=project_id,
                offer=offer,
                payload=input_payload,
            )
        elif (
            offer.adapter_id == NativeVideoClawAdapter.adapter_id
            and offer.offer_id == "native_videoclaw.edge_tts"
        ):
            result = await native_videoclaw.execute(
                project_id=project_id,
                offer=offer,
                preparation=preparation,
                payload=input_payload,
            )
        elif offer.adapter_id.startswith("mcp."):
            result = await mcp_execution.execute(
                project_id=project_id,
                offer=offer,
                preparation=preparation,
                payload=input_payload,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "adapter_not_executable_yet",
                    "message": (
                        f"offer {offer.offer_id!r} passed selection/authorization, but adapter "
                        f"{offer.adapter_id!r} has no execution transport in this slice"
                    ),
                },
            )
    except InvalidCapabilityInput as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except CapabilityToolUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except UnsupportedCapabilityExecution as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except CapabilityToolFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except MCPBindingExecutionRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "mcp_binding_rejected", "message": str(exc)},
        ) from exc
    except MCPExecutionInputRejected as exc:
        raise _mcp_error(exc, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from exc
    except MCPRequestTooLarge as exc:
        raise _mcp_error(exc, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from exc
    except MCPCallTimeout as exc:
        raise _mcp_error(exc, status_code=status.HTTP_504_GATEWAY_TIMEOUT) from exc
    except (MCPToolReturnedError, MCPResponseTooLarge, MCPCallError) as exc:
        raise _mcp_error(exc, status_code=status.HTTP_502_BAD_GATEWAY) from exc

    return CapabilityExecutionEnvelope(selection=decision, result=result).to_dict()
