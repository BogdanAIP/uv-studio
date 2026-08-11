"""External capability preparation, consent authorization and run provenance API."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import CapabilityRegistry
from uv_studio.capabilities.consent import (
    ExecutionAuthorizationStore,
    ExecutionConsentRequired,
    ExternalExecutionError,
    PreparedExternalExecution,
    prepare_external_execution,
)
from uv_studio.capabilities.external_runs import ExternalRunStore, ExternalRunStoreError
from uv_studio.capabilities.registry import UnknownCapability
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

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio External Execution"])


@lru_cache(maxsize=1)
def get_execution_authorization_store() -> ExecutionAuthorizationStore:
    return ExecutionAuthorizationStore()


def get_external_run_store(
    store: ProjectStore = Depends(get_project_store),
) -> ExternalRunStore:
    return ExternalRunStore(store)


def parse_selection_policy(value: Any) -> SelectionPolicy:
    if value is None:
        return SelectionPolicy.LOCAL_FREE_FIRST
    try:
        return SelectionPolicy(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="selection_policy must be manual, pinned_offer, or local_free_first",
        ) from exc


def require_project(store: ProjectStore, project_id: str) -> None:
    try:
        store.load_project(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def select_execution_offer(
    registry: CapabilityRegistry,
    capability_id: str,
    *,
    policy: SelectionPolicy,
    offer_id: str | None,
):
    try:
        return select_offer(
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


def prepare_from_request(
    *,
    project_id: str,
    capability_id: str,
    request: Mapping[str, Any],
    registry: CapabilityRegistry,
) -> tuple[Any, PreparedExternalExecution, Mapping[str, Any]]:
    policy = parse_selection_policy(request.get("selection_policy"))
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
    decision = select_execution_offer(
        registry,
        capability_id,
        policy=policy,
        offer_id=offer_id,
    )
    offer = decision.offer
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="selection policy did not produce an executable offer",
        )
    try:
        prepared = prepare_external_execution(
            project_id=project_id,
            offer=offer,
            payload=input_payload,
        )
    except ExternalExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return decision, prepared, input_payload


@router.post("/{project_id}/capabilities/{capability_id}/prepare-execution")
def prepare_project_external_execution(
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
) -> dict[str, Any]:
    allowed = {"selection_policy", "offer_id", "input"}
    unknown = set(request).difference(allowed)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unsupported prepare-execution fields: {sorted(unknown)!r}",
        )
    require_project(store, project_id)
    decision, prepared, _ = prepare_from_request(
        project_id=project_id,
        capability_id=capability_id,
        request=request,
        registry=registry,
    )
    return {"selection": decision.to_dict(), "prepared": prepared.to_dict()}


@router.post("/{project_id}/capabilities/{capability_id}/authorize-execution")
def authorize_project_external_execution(
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    grants: ExecutionAuthorizationStore = Depends(get_execution_authorization_store),
) -> dict[str, Any]:
    allowed = {
        "selection_policy",
        "offer_id",
        "input",
        "confirm_remote",
        "confirm_cost",
        "acknowledge_unknown_cost",
    }
    unknown = set(request).difference(allowed)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unsupported authorize-execution fields: {sorted(unknown)!r}",
        )
    require_project(store, project_id)
    decision, prepared, _ = prepare_from_request(
        project_id=project_id,
        capability_id=capability_id,
        request=request,
        registry=registry,
    )
    if not prepared.authorization_required:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "authorization_not_required",
                "message": "selected offer does not require external execution authorization",
                "prepared": prepared.to_dict(),
            },
        )
    for field in ("confirm_remote", "confirm_cost", "acknowledge_unknown_cost"):
        if field in request and not isinstance(request[field], bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} must be boolean",
            )
    try:
        grant = grants.authorize(
            prepared,
            confirm_remote=request.get("confirm_remote", False),
            confirm_cost=request.get("confirm_cost", False),
            acknowledge_unknown_cost=request.get("acknowledge_unknown_cost", False),
        )
    except ExecutionConsentRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "consent_required",
                "message": str(exc),
                "prepared": prepared.to_dict(),
            },
        ) from exc
    return {
        "selection": decision.to_dict(),
        "prepared": prepared.to_dict(),
        "authorization": grant.public_dict(),
    }


@router.get("/{project_id}/external-runs/{run_id}")
def get_project_external_run(
    project_id: str,
    run_id: str,
    store: ProjectStore = Depends(get_project_store),
    runs: ExternalRunStore = Depends(get_external_run_store),
) -> dict[str, Any]:
    require_project(store, project_id)
    try:
        return runs.load(project_id, run_id).to_dict()
    except (ExternalRunStoreError, ProjectValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External run not found",
        ) from exc
