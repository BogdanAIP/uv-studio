"""UV-owned API for approving provider-neutral replacement plans."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    ProjectStore,
    ReplacementPlan,
    ReplacementPlanError,
    ReplacementPlanNotFound,
    ReplacementPlanProposal,
    ReplacementPlanState,
    ReplacementPlanStore,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Replacement Plans"])


class ReplacementPlanProposalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edit_id: StrictStr
    method_class: Literal["deterministic_edit", "prepared_asset", "generative_transform"]
    goal: StrictStr
    required_changes: list[StrictStr]
    allowed_changes: list[StrictStr] = Field(default_factory=list)
    forbidden_changes: list[StrictStr] = Field(default_factory=list)
    audio_strategy: Literal["preserve_source", "replacement_audio"] = "preserve_source"


class ReplacementPlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: StrictInt
    edit_id: StrictStr
    source_path: StrictStr
    start_us: StrictInt
    end_us: StrictInt
    brief_sha256: StrictStr
    method_class: Literal["deterministic_edit", "prepared_asset", "generative_transform"]
    goal: StrictStr
    required_changes: list[StrictStr]
    allowed_changes: list[StrictStr]
    forbidden_changes: list[StrictStr]
    audio_strategy: Literal["preserve_source", "replacement_audio"]
    sample_policy: Literal["not_required", "required_before_full_generation"]
    constraint_ids: list[StrictStr]
    review_target_ids: list[StrictStr]


class ReplacementPlanStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: StrictInt
    plans: list[ReplacementPlanPayload]


def _state_payload(state: ReplacementPlanState) -> ReplacementPlanStatePayload:
    return ReplacementPlanStatePayload.model_validate(state.to_dict())


def _plan_payload(plan: ReplacementPlan) -> ReplacementPlanPayload:
    return ReplacementPlanPayload.model_validate(plan.to_dict())


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, ReplacementPlanNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replacement plan not found")
    if isinstance(exc, ReplacementPlanError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Replacement plan operation failed",
    )


@router.get("/{project_id}/replacement-plans", response_model=ReplacementPlanStatePayload)
def list_replacement_plans(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ReplacementPlanStatePayload:
    try:
        store.load_project(project_id)
        return _state_payload(ReplacementPlanStore(store).load(project_id))
    except (ProjectNotFound, ReplacementPlanError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/replacement-plans/{edit_id}", response_model=ReplacementPlanPayload)
def get_replacement_plan(
    project_id: str,
    edit_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ReplacementPlanPayload:
    try:
        store.load_project(project_id)
        plan = ReplacementPlanStore(store).load(project_id).get(edit_id)
        return _plan_payload(plan)
    except (ProjectNotFound, ReplacementPlanError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.put("/{project_id}/replacement-plans/{edit_id}", response_model=ReplacementPlanStatePayload)
def approve_replacement_plan(
    project_id: str,
    edit_id: str,
    request: ReplacementPlanProposalPayload,
    store: ProjectStore = Depends(get_project_store),
) -> ReplacementPlanStatePayload:
    try:
        store.load_project(project_id)
        if request.edit_id != edit_id:
            raise ReplacementPlanError("URL edit_id must exactly match proposal edit_id")
        proposal = ReplacementPlanProposal.from_dict(request.model_dump())
        return _state_payload(ReplacementPlanStore(store).approve(project_id, proposal))
    except (ProjectNotFound, ReplacementPlanError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.delete("/{project_id}/replacement-plans/{edit_id}", response_model=ReplacementPlanStatePayload)
def delete_replacement_plan(
    project_id: str,
    edit_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ReplacementPlanStatePayload:
    try:
        store.load_project(project_id)
        return _state_payload(ReplacementPlanStore(store).remove(project_id, edit_id))
    except (ProjectNotFound, ReplacementPlanError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
