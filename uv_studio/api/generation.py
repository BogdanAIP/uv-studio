"""Studio named-model generation API over the canonical generation service."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import get_execution_authorization_store
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities.authorization import (
    ConsentScope,
    ExecutionAuthorizationError,
    ExecutionConsentRequired,
    OneShotAuthorizationStore,
    prepare_execution,
)
from uv_studio.capabilities.selection import SelectionPolicy
from uv_studio.generation.builtin import build_builtin_model_registry
from uv_studio.generation.jobs import (
    GenerationJobConflict,
    GenerationJobError,
    GenerationJobNotFound,
    GenerationStatus,
)
from uv_studio.generation.models import (
    GenerationContract,
    GenerationValidationError,
    ModelRegistry,
    ModelRegistryError,
    UnknownModel,
)
from uv_studio.generation.service import (
    GenerationExecutor,
    GenerationService,
    GenerationServiceError,
    UnavailableGenerationExecutor,
)
from uv_studio.production.semantics import ProductionSemanticError
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv", tags=["UV Studio Named Generation"])


class _GenerationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=128)
    inputs: dict[str, Any] = Field(default_factory=dict)
    contract: dict[str, Any] = Field(default_factory=dict)


class GenerationPrepareRequest(_GenerationBase):
    pass


class GenerationAuthorizeRequest(_GenerationBase):
    acknowledgements: list[str] = Field(default_factory=list)


class GenerationSubmitRequest(_GenerationBase):
    idempotency_key: str = Field(min_length=1, max_length=128)
    authorization_token: str | None = None


class GenerationRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    authorization_token: str | None = None


def get_model_registry(
    capability_registry=Depends(get_capability_registry),
) -> ModelRegistry:
    return build_builtin_model_registry(capability_registry)


def get_generation_executor() -> GenerationExecutor:
    return UnavailableGenerationExecutor()


def get_generation_service(
    store: ProjectStore = Depends(get_project_store),
    models: ModelRegistry = Depends(get_model_registry),
    authorizations: OneShotAuthorizationStore = Depends(get_execution_authorization_store),
    executor: GenerationExecutor = Depends(get_generation_executor),
) -> GenerationService:
    return GenerationService(store, models, authorizations, executor)


def _contract(data: dict[str, Any]) -> GenerationContract:
    return GenerationContract.from_dict(data)


def _acknowledgements(values: list[str]) -> set[ConsentScope]:
    try:
        scopes = [ConsentScope(value) for value in values]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid generation authorization acknowledgement",
        ) from exc
    if len(set(scopes)) != len(scopes):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="generation authorization acknowledgements must be unique",
        )
    return set(scopes)


def _raise_generation_error(exc: Exception) -> None:
    if isinstance(exc, (UnknownModel, GenerationJobNotFound, ProjectNotFound)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc) or "Not found") from exc
    if isinstance(exc, ExecutionConsentRequired):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "consent_required", "message": str(exc)},
        ) from exc
    if isinstance(exc, ExecutionAuthorizationError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "authorization_invalid", "message": str(exc)},
        ) from exc
    if isinstance(exc, GenerationJobConflict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "generation_job_conflict", "message": str(exc)},
        ) from exc
    if isinstance(
        exc,
        (
            GenerationValidationError,
            ProductionSemanticError,
            ProjectValidationError,
            ProjectStoreError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, (GenerationJobError, ModelRegistryError, GenerationServiceError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


def _prepare(service: GenerationService, project_id: str, request: _GenerationBase):
    return service.prepare(
        project_id=project_id,
        shot_id=request.shot_id,
        model_id=request.model_id,
        inputs=request.inputs,
        contract=_contract(request.contract),
    )


def _schedule_run(service: GenerationService, project_id: str, job_id: str) -> None:
    try:
        service.run(project_id, job_id)
    except Exception:
        # The durable Job/Attempt record is the user-visible failure surface.
        # Background execution must not convert a recorded provider failure into
        # an unrelated server response after the 202 submission was returned.
        return


@router.get("/models")
def list_named_models(models: ModelRegistry = Depends(get_model_registry)) -> list[dict[str, Any]]:
    return list(models.catalog())


@router.get("/models/{model_id}")
def get_named_model(
    model_id: str,
    models: ModelRegistry = Depends(get_model_registry),
) -> dict[str, Any]:
    try:
        return models.describe(model_id)
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


@router.post("/projects/{project_id}/studio/generation/prepare")
def prepare_generation(
    project_id: str,
    request: GenerationPrepareRequest,
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    try:
        prepared = _prepare(service, project_id, request)
        payload = prepared.to_dict()
        payload["model"] = service.model_registry.describe(prepared.model.model_id)
        return payload
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


@router.post("/projects/{project_id}/studio/generation/authorize")
def authorize_generation(
    project_id: str,
    request: GenerationAuthorizeRequest,
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    try:
        prepared = _prepare(service, project_id, request)
        token, expires_at = service.authorizations.issue(
            prepared.execution,
            acknowledgements=_acknowledgements(request.acknowledgements),
        )
        return {
            "model": service.model_registry.describe(prepared.model.model_id),
            "request_digest": prepared.request_digest,
            "authorization": prepared.execution.to_dict(),
            "authorization_token": token,
            "expires_at_unix": expires_at,
        }
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


@router.post(
    "/projects/{project_id}/studio/generation/jobs",
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_generation(
    project_id: str,
    request: GenerationSubmitRequest,
    background_tasks: BackgroundTasks,
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    try:
        result = service.submit(
            project_id=project_id,
            shot_id=request.shot_id,
            model_id=request.model_id,
            inputs=request.inputs,
            contract=_contract(request.contract),
            idempotency_key=request.idempotency_key,
            authorization_token=request.authorization_token,
        )
        if not result.reused and result.job.status is GenerationStatus.QUEUED:
            background_tasks.add_task(
                _schedule_run,
                service,
                project_id,
                result.job.job_id,
            )
        return result.to_dict()
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


@router.get("/projects/{project_id}/studio/generation/jobs")
def list_generation_jobs(
    project_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> list[dict[str, Any]]:
    try:
        return [job.to_dict() for job in service.jobs.list(project_id)]
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


@router.get("/projects/{project_id}/studio/generation/jobs/{job_id}")
def get_generation_job(
    project_id: str,
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    try:
        return service.jobs.get(project_id, job_id).to_dict()
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


def _retry_preparation(service: GenerationService, project_id: str, job_id: str):
    job = service.jobs.get(project_id, job_id)
    if job.status is not GenerationStatus.FAILED:
        raise GenerationJobConflict("only a failed generation job can be retried")
    mapping = job.request.get("execution_mapping")
    if not isinstance(mapping, dict):
        raise GenerationJobError("generation job lost execution mapping")
    offer_id = mapping.get("offer_id")
    if not isinstance(offer_id, str):
        raise GenerationJobError("generation job lost offer identity")
    offer = service.model_registry.capability_registry.get_offer(offer_id)
    return job, prepare_execution(
        project_id=project_id,
        offer=offer,
        selection_policy=SelectionPolicy.PINNED_OFFER,
        payload=job.request,
    )


@router.post("/projects/{project_id}/studio/generation/jobs/{job_id}/prepare-retry")
def prepare_generation_retry(
    project_id: str,
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    try:
        job, preparation = _retry_preparation(service, project_id, job_id)
        return {"job": job.to_dict(), "authorization": preparation.to_dict()}
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


@router.post("/projects/{project_id}/studio/generation/jobs/{job_id}/retry")
def retry_generation(
    project_id: str,
    job_id: str,
    request: GenerationRetryRequest,
    background_tasks: BackgroundTasks,
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    try:
        job, preparation = _retry_preparation(service, project_id, job_id)
        service.authorizations.consume(request.authorization_token, preparation)
        background_tasks.add_task(_schedule_run, service, project_id, job.job_id)
        return job.to_dict()
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")


@router.post("/projects/{project_id}/studio/generation/jobs/{job_id}/cancel")
def cancel_generation(
    project_id: str,
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    try:
        return service.cancel(project_id, job_id).to_dict()
    except Exception as exc:
        _raise_generation_error(exc)
        raise AssertionError("unreachable")
