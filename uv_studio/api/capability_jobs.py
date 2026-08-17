"""Cancellable process-backed capability jobs.

The synchronous capability execution API remains the compatibility path. This router
adds an explicit job contract only for adapters that can prove process-level
cancellation; unsupported adapters fail closed instead of pretending to cancel.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    _consent_required_detail,
    _prepare,
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
)
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.authorization import (
    ExecutionAuthorizationInvalid,
    ExecutionConsentRequired,
    OneShotAuthorizationStore,
)
from uv_studio.capabilities.execution import CapabilityExecutionEnvelope
from uv_studio.capabilities.jobs import (
    CapabilityExecutionJobStore,
    CapabilityJobCapacityExceeded,
    CapabilityJobNotFound,
)
from uv_studio.capabilities.models import CostClass, LocalityClass
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.projects.store import ProjectStore

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Capability Jobs"])


@lru_cache(maxsize=1)
def get_capability_job_store() -> CapabilityExecutionJobStore:
    return CapabilityExecutionJobStore()


def _job_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "capability_job_not_found", "message": "Capability job not found"},
    )


def _supports_cancellation(adapter: Any, capability_id: str) -> bool:
    check = getattr(adapter, "supports_cancellation", None)
    if not callable(check):
        return False
    try:
        return check(capability_id) is True
    except Exception:
        return False


@router.post(
    "/{project_id}/capabilities/{capability_id}/jobs",
    status_code=status.HTTP_202_ACCEPTED,
)
def start_capability_job(
    project_id: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    local_ffmpeg: LocalFFmpegAdapter = Depends(get_local_ffmpeg_adapter),
    authorizations: OneShotAuthorizationStore = Depends(get_execution_authorization_store),
    jobs: CapabilityExecutionJobStore = Depends(get_capability_job_store),
) -> dict[str, Any]:
    decision, preparation, input_payload = _prepare(
        project_id=project_id,
        capability_id=capability_id,
        request=request,
        store=store,
        registry=registry,
        allow_authorization_token=True,
    )
    offer = decision.offer
    if (
        offer.adapter_id != LocalFFmpegAdapter.adapter_id
        or offer.locality is not LocalityClass.LOCAL
        or offer.cost_class is not CostClass.FREE
        or not _supports_cancellation(local_ffmpeg, capability_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "capability_job_cancellation_not_supported",
                "message": (
                    "selected offer has no proven cancellable process boundary; "
                    "use synchronous execution or another cancellable offer"
                ),
            },
        )

    authorization_token = request.get("authorization_token")
    if authorization_token is not None and not isinstance(authorization_token, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="authorization_token must be a string when provided",
        )
    try:
        authorizations.consume(authorization_token, preparation)
    except ExecutionConsentRequired as exc:
        detail = _consent_required_detail(preparation)
        detail["message"] = str(exc)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    except ExecutionAuthorizationInvalid as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "authorization_invalid", "message": str(exc)},
        ) from exc

    def execute(cancellation):
        result = local_ffmpeg.execute(
            project_id=project_id,
            offer=offer,
            payload=input_payload,
            cancellation=cancellation,
        )
        return CapabilityExecutionEnvelope(selection=decision, result=result).to_dict()

    try:
        return jobs.create(
            project_id=project_id,
            capability_id=capability_id,
            offer_id=offer.offer_id,
            adapter_id=offer.adapter_id,
            executor=execute,
        )
    except CapabilityJobCapacityExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "capability_job_capacity_exceeded", "message": str(exc)},
        ) from exc


@router.get("/{project_id}/capability-jobs/{job_id}")
def get_capability_job(
    project_id: str,
    job_id: str,
    jobs: CapabilityExecutionJobStore = Depends(get_capability_job_store),
) -> dict[str, Any]:
    try:
        return jobs.get(project_id=project_id, job_id=job_id)
    except CapabilityJobNotFound as exc:
        raise _job_not_found() from exc


@router.post("/{project_id}/capability-jobs/{job_id}/cancel")
def cancel_capability_job(
    project_id: str,
    job_id: str,
    jobs: CapabilityExecutionJobStore = Depends(get_capability_job_store),
) -> dict[str, Any]:
    try:
        return jobs.cancel(project_id=project_id, job_id=job_id)
    except CapabilityJobNotFound as exc:
        raise _job_not_found() from exc
