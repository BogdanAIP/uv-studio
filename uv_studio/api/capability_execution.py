"""Project-scoped capability execution API.

The endpoint executes only implementations explicitly permitted by current
selection policy. This Stage 3 slice intentionally exposes local deterministic
execution only; external/MCP/paid runtimes remain metadata-only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import (
    CapabilityExecutionEnvelope,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from uv_studio.capabilities.models import CostClass, LocalityClass
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.capabilities.selection import (
    NoEligibleOffer,
    OfferSelectionError,
    OfferSelectionRequired,
    PinnedOfferRejected,
    SelectionPolicy,
    select_offer,
)
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Capability Execution"])


def get_local_ffmpeg_adapter(
    store: ProjectStore = Depends(get_project_store),
) -> LocalFFmpegAdapter:
    return LocalFFmpegAdapter(store)


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


@router.post("/{project_id}/capabilities/{capability_id}/execute")
def execute_project_capability(
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    local_ffmpeg: LocalFFmpegAdapter = Depends(get_local_ffmpeg_adapter),
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="request body must be a JSON object",
        )

    unknown_fields = set(request).difference({"selection_policy", "offer_id", "input"})
    if unknown_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unsupported execution request fields: {sorted(unknown_fields)!r}",
        )

    try:
        store.load_project(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

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

    offer = decision.offer
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="selection policy did not produce an executable offer",
        )

    # Stage 3 local slice: known external/remote/paid offers remain metadata-only.
    if (
        offer.adapter_id != LocalFFmpegAdapter.adapter_id
        or offer.cost_class is not CostClass.FREE
        or offer.locality is not LocalityClass.LOCAL
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "adapter_not_executable_yet",
                "message": (
                    f"offer {offer.offer_id!r} is known but current Stage 3 execution permits "
                    "only free/local local_ffmpeg offers"
                ),
            },
        )

    try:
        result = local_ffmpeg.execute(
            project_id=project_id,
            offer=offer,
            payload=input_payload,
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

    return CapabilityExecutionEnvelope(selection=decision, result=result).to_dict()
