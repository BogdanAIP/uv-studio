"""Stage 4B replacement candidate preparation without automatic acceptance."""

from __future__ import annotations

import re
import shutil
import uuid
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, StrictStr

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    authorize_project_capability_execution,
    execute_project_capability,
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
    get_mcp_execution_adapter,
    get_native_videoclaw_adapter,
    prepare_project_capability_execution,
)
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import CostClass, LocalityClass, MediaKind, OperationKind
from uv_studio.capabilities.adapters import LocalFFmpegAdapter, NativeVideoClawAdapter
from uv_studio.capabilities.adapters.mcp_execution import MCPExecutionAdapter
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability
from uv_studio.projects.models import ProjectReference, ProjectValidationError, validate_project_relative_path
from uv_studio.projects.replacement_candidate import (
    ReplacementCandidateError,
    ReplacementCandidateNotFound,
    ReplacementCandidateState,
    ReplacementCandidateStore,
    replacement_plan_sha256,
)
from uv_studio.projects.replacement_plan import ReplacementPlan
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Replacement Preparation"])
_SAFE_VIDEO_SUFFIXES = frozenset({".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"})
_SAFE_SUFFIX_RE = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9._-]{0,15}$")


class PreparedAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edit_id: StrictStr
    source_path: StrictStr


class SampleApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: StrictStr


def _candidate_store(store: ProjectStore) -> ReplacementCandidateStore:
    return ReplacementCandidateStore(store)


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=404, detail="Project not found")
    if isinstance(exc, ReplacementCandidateNotFound):
        return HTTPException(status_code=404, detail="Replacement candidate not found")
    if isinstance(exc, (ReplacementCandidateError, ProjectValidationError, ProjectStoreError)):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Replacement preparation failed")


def _request_parts(
    request: Mapping[str, Any], *, extra_allowed: set[str]
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    if not isinstance(request, Mapping):
        raise HTTPException(status_code=422, detail="request body must be a JSON object")
    allowed = {"stage", "selection_policy", "offer_id", "input", *extra_allowed}
    unknown = set(request).difference(allowed)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported candidate execution fields: {sorted(unknown)!r}",
        )
    stage = request.get("stage")
    if stage not in {"sample", "full"}:
        raise HTTPException(status_code=422, detail="stage must be 'sample' or 'full'")
    generic = {key: value for key, value in request.items() if key != "stage"}
    preflight = {key: value for key, value in generic.items() if key not in extra_allowed}
    return stage, generic, preflight


def _current_plan(store: ProjectStore, project_id: str, edit_id: str) -> ReplacementPlan:
    try:
        store.load_project(project_id)
        return _candidate_store(store).current_plan(project_id, edit_id)
    except (ProjectNotFound, ReplacementCandidateError, ProjectStoreError) as exc:
        raise _translate_error(exc) from exc


def _require_current_sample(store: ProjectStore, project_id: str, plan: ReplacementPlan) -> None:
    candidates = _candidate_store(store)
    state = candidates.load(project_id)
    digest = replacement_plan_sha256(plan)
    approval = next(
        (
            item
            for item in state.sample_approvals
            if item.edit_id == plan.edit_id and item.plan_sha256 == digest
        ),
        None,
    )
    if approval is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "sample_approval_required",
                "message": "full generative preparation requires an approved sample for the current plan",
            },
        )
    try:
        sample = candidates.validate_candidate(project_id, approval.candidate_id)
    except ReplacementCandidateError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "sample_approval_stale", "message": str(exc)},
        ) from exc
    if sample.stage != "sample" or sample.method_class != "generative_transform":
        raise HTTPException(
            status_code=409,
            detail={"code": "sample_approval_stale", "message": "approved sample is not a current generative sample"},
        )


def _validate_capability_path(
    *,
    store: ProjectStore,
    project_id: str,
    plan: ReplacementPlan,
    stage: str,
    capability_id: str,
    prepared: Mapping[str, Any],
    registry: CapabilityRegistry,
) -> None:
    try:
        definition = registry.get_capability(capability_id)
    except UnknownCapability as exc:
        raise HTTPException(status_code=404, detail="Capability not found") from exc
    offer = prepared.get("selection", {}).get("offer")
    if not isinstance(offer, Mapping):
        raise HTTPException(status_code=409, detail="candidate preparation did not resolve an offer")
    if MediaKind.VIDEO not in definition.outputs:
        raise HTTPException(
            status_code=409,
            detail={"code": "candidate_output_kind_rejected", "message": "replacement candidate capability must produce video"},
        )

    if plan.method_class == "prepared_asset":
        raise HTTPException(
            status_code=409,
            detail={"code": "method_class_mismatch", "message": "prepared_asset plans use the project-asset endpoint"},
        )
    if plan.method_class == "deterministic_edit":
        if stage != "full":
            raise HTTPException(status_code=409, detail={"code": "method_class_mismatch", "message": "deterministic plans only produce full candidates"})
        if definition.operation_kind not in {OperationKind.DETERMINISTIC_MEDIA, OperationKind.ASSEMBLY}:
            raise HTTPException(status_code=409, detail={"code": "method_class_mismatch", "message": "deterministic_edit requires deterministic media or assembly capability"})
        if offer.get("locality") != LocalityClass.LOCAL.value or offer.get("cost_class") != CostClass.FREE.value:
            raise HTTPException(status_code=409, detail={"code": "method_class_mismatch", "message": "deterministic_edit cannot widen to remote or non-free execution"})
        return
    if plan.method_class == "generative_transform":
        if definition.operation_kind not in {OperationKind.GENERATION, OperationKind.TRANSFORMATION}:
            raise HTTPException(status_code=409, detail={"code": "method_class_mismatch", "message": "generative_transform requires generation or transformation capability"})
        if stage == "full":
            _require_current_sample(store, project_id, plan)
        return
    raise HTTPException(status_code=409, detail={"code": "method_class_mismatch", "message": "unsupported approved method class"})


def _candidate_preflight(
    *,
    project_id: str,
    edit_id: str,
    capability_id: str,
    request: Mapping[str, Any],
    extra_allowed: set[str],
    store: ProjectStore,
    registry: CapabilityRegistry,
) -> tuple[str, dict[str, Any], dict[str, Any], ReplacementPlan]:
    stage, generic, preflight = _request_parts(request, extra_allowed=extra_allowed)
    plan = _current_plan(store, project_id, edit_id)
    prepared = prepare_project_capability_execution(
        project_id,
        capability_id,
        preflight,
        store=store,
        registry=registry,
    )
    _validate_capability_path(
        store=store,
        project_id=project_id,
        plan=plan,
        stage=stage,
        capability_id=capability_id,
        prepared=prepared,
        registry=registry,
    )
    return stage, generic, prepared, plan


def _state(state: ReplacementCandidateState) -> dict[str, Any]:
    return state.to_dict()


@router.get("/{project_id}/replacement-candidates")
def list_replacement_candidates(
    project_id: str, store: ProjectStore = Depends(get_project_store)
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        return _state(_candidate_store(store).load(project_id))
    except (ProjectNotFound, ReplacementCandidateError, ProjectStoreError) as exc:
        raise _translate_error(exc) from exc


@router.get("/{project_id}/replacement-candidates/{candidate_id}")
def get_replacement_candidate(
    project_id: str,
    candidate_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        return _candidate_store(store).load(project_id).get(candidate_id).to_dict()
    except (ProjectNotFound, ReplacementCandidateError, ProjectStoreError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{project_id}/replacement-candidates/{candidate_id}")
def remove_replacement_candidate(
    project_id: str,
    candidate_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        return _state(_candidate_store(store).remove(project_id, candidate_id))
    except (ProjectNotFound, ReplacementCandidateError, ProjectStoreError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{project_id}/replacement-candidates/{candidate_id}/approve-sample")
def approve_replacement_sample(
    project_id: str,
    candidate_id: str,
    request: SampleApprovalRequest,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    if request.candidate_id != candidate_id:
        raise HTTPException(status_code=422, detail="URL candidate_id must match request candidate_id")
    try:
        store.load_project(project_id)
        return _state(_candidate_store(store).approve_sample(project_id, candidate_id))
    except (ProjectNotFound, ReplacementCandidateError, ProjectStoreError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{project_id}/replacement-candidates/prepared-asset")
def prepare_project_asset_candidate(
    project_id: str,
    request: PreparedAssetRequest,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    plan = _current_plan(store, project_id, request.edit_id)
    if plan.method_class != "prepared_asset":
        raise HTTPException(status_code=409, detail={"code": "method_class_mismatch", "message": "current approved plan is not prepared_asset"})
    try:
        canonical = validate_project_relative_path(request.source_path)
        source = store.resolve_project_file(
            project_id,
            canonical,
            must_exist=True,
            allowed_roots=("sources", "assets", "artifacts", "exports"),
        )
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(status_code=422, detail="source_path must be an existing project file") from exc
    if not source.is_file() or source.is_symlink() or source.stat().st_size <= 0:
        raise HTTPException(status_code=422, detail="prepared source must be a non-empty regular project file")
    suffix = source.suffix.lower()
    if not _SAFE_SUFFIX_RE.fullmatch(suffix) or suffix not in _SAFE_VIDEO_SUFFIXES:
        raise HTTPException(status_code=422, detail="prepared source must use a supported video file extension")

    artifact_id = f"art_{uuid.uuid4().hex}"
    candidate_id = f"cand_{uuid.uuid4().hex}"
    relative_path = f"artifacts/{artifact_id}{suffix}"
    artifact_path = store.resolve_project_file(project_id, relative_path, allowed_roots=("artifacts",))
    reference = ProjectReference(
        id=artifact_id,
        kind="video",
        path=relative_path,
        metadata={
            "lifecycle": "replacement_candidate",
            "method_class": "prepared_asset",
            "source_asset_path": canonical,
        },
    )
    registered = False
    try:
        if artifact_path.exists() or artifact_path.is_symlink():
            raise ReplacementCandidateError("allocated candidate artifact already exists")
        shutil.copyfile(source, artifact_path)
        if artifact_path.stat().st_size <= 0:
            raise ReplacementCandidateError("prepared candidate artifact must not be empty")
        project = store.load_project(project_id)
        store.update_project(project_id, artifacts=(*project.artifacts, reference))
        registered = True
        candidates = _candidate_store(store)
        candidate = candidates.make_candidate(
            project_id,
            candidate_id=candidate_id,
            edit_id=plan.edit_id,
            stage="full",
            artifact_id=artifact_id,
            artifact_path=relative_path,
        )
        state = candidates.register(project_id, candidate)
        return {"candidate": candidate.to_dict(), "state": state.to_dict()}
    except Exception as exc:
        if registered:
            try:
                project = store.load_project(project_id)
                store.update_project(
                    project_id,
                    artifacts=tuple(item for item in project.artifacts if item.id != artifact_id),
                )
            except Exception:
                pass
        try:
            artifact_path.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, ReplacementCandidateError):
            raise _translate_error(exc) from exc
        raise


@router.post("/{project_id}/replacement-candidates/{edit_id}/{stage}/capabilities/{capability_id}/prepare-execution")
def prepare_candidate_capability_execution(
    project_id: str,
    edit_id: str,
    stage: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
) -> dict[str, Any]:
    _stage, _generic, prepared, plan = _candidate_preflight(
        project_id=project_id,
        edit_id=edit_id,
        capability_id=capability_id,
        request={**request, "stage": stage},
        extra_allowed=set(),
        store=store,
        registry=registry,
    )
    return {"plan_sha256": replacement_plan_sha256(plan), **prepared}


@router.post("/{project_id}/replacement-candidates/{edit_id}/{stage}/capabilities/{capability_id}/authorize-execution")
def authorize_candidate_capability_execution(
    project_id: str,
    edit_id: str,
    stage: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    authorizations: OneShotAuthorizationStore = Depends(get_execution_authorization_store),
) -> dict[str, Any]:
    _stage, generic, _prepared, plan = _candidate_preflight(
        project_id=project_id,
        edit_id=edit_id,
        capability_id=capability_id,
        request={**request, "stage": stage},
        extra_allowed={"acknowledgements"},
        store=store,
        registry=registry,
    )
    authorized = authorize_project_capability_execution(
        project_id,
        capability_id,
        generic,
        store=store,
        registry=registry,
        authorizations=authorizations,
    )
    return {"plan_sha256": replacement_plan_sha256(plan), **authorized}


@router.post("/{project_id}/replacement-candidates/{edit_id}/{stage}/capabilities/{capability_id}/execute")
async def execute_candidate_capability(
    project_id: str,
    edit_id: str,
    stage: str,
    capability_id: str,
    request: dict[str, Any],
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    local_ffmpeg: LocalFFmpegAdapter = Depends(get_local_ffmpeg_adapter),
    native_videoclaw: NativeVideoClawAdapter = Depends(get_native_videoclaw_adapter),
    mcp_execution: MCPExecutionAdapter = Depends(get_mcp_execution_adapter),
    authorizations: OneShotAuthorizationStore = Depends(get_execution_authorization_store),
) -> dict[str, Any]:
    _stage, generic, _prepared, plan = _candidate_preflight(
        project_id=project_id,
        edit_id=edit_id,
        capability_id=capability_id,
        request={**request, "stage": stage},
        extra_allowed={"authorization_token"},
        store=store,
        registry=registry,
    )
    envelope = await execute_project_capability(
        project_id,
        capability_id,
        generic,
        store=store,
        registry=registry,
        local_ffmpeg=local_ffmpeg,
        native_videoclaw=native_videoclaw,
        mcp_execution=mcp_execution,
        authorizations=authorizations,
    )
    result = envelope.get("result")
    artifact = result.get("artifact") if isinstance(result, Mapping) else None
    if not isinstance(artifact, Mapping):
        raise HTTPException(status_code=502, detail={"code": "candidate_artifact_missing", "message": "capability execution did not return a project artifact"})
    if artifact.get("kind") != "video":
        raise HTTPException(status_code=502, detail={"code": "candidate_artifact_kind_invalid", "message": "replacement candidate must be a video artifact"})
    artifact_id = artifact.get("id")
    artifact_path = artifact.get("path")
    if not isinstance(artifact_id, str) or not isinstance(artifact_path, str):
        raise HTTPException(status_code=502, detail={"code": "candidate_artifact_invalid", "message": "project artifact is missing id/path"})
    output = result.get("output") if isinstance(result, Mapping) else None
    run_id = output.get("run_id") if isinstance(output, Mapping) and isinstance(output.get("run_id"), str) else None
    candidates = _candidate_store(store)
    try:
        candidate = candidates.make_candidate(
            project_id,
            candidate_id=f"cand_{uuid.uuid4().hex}",
            edit_id=plan.edit_id,
            stage=stage,
            artifact_id=artifact_id,
            artifact_path=artifact_path,
            execution_run_id=run_id,
        )
        state = candidates.register(project_id, candidate)
    except ReplacementCandidateError as exc:
        raise _translate_error(exc) from exc
    return {
        "candidate": candidate.to_dict(),
        "candidate_state": state.to_dict(),
        "execution": envelope,
    }
