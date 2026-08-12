"""UV-owned HTTP API for provider-neutral RangeContinuityBrief state."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr

from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    ContinuityBriefError,
    ContinuityBriefNotFound,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefState,
    RangeContinuityBriefStore,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Continuity Briefs"])


class ContinuityEvidencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: StrictStr
    role: Literal["before", "requested", "after", "reference"]
    path: StrictStr
    source_start_us: StrictInt | None = None
    source_end_us: StrictInt | None = None


class MechanicalFactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: StrictStr
    key: StrictStr
    value: StrictStr | StrictInt | StrictBool
    unit: StrictStr | None = None
    evidence_ids: list[StrictStr] = []


class ContinuityObservationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: StrictStr
    kind: Literal["observation", "inference"]
    statement: StrictStr
    confidence: Literal["low", "medium", "high"]
    evidence_ids: list[StrictStr]


class ContinuityConstraintPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_id: StrictStr
    category: Literal["visual", "motion", "audio", "timing", "content", "technical", "style"]
    requirement: StrictStr
    evidence_ids: list[StrictStr] = []


class ReviewTargetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: StrictStr
    criterion: StrictStr
    required: StrictBool = True
    evidence_ids: list[StrictStr] = []


class RangeContinuityBriefPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: StrictInt = 1
    edit_id: StrictStr
    source_path: StrictStr
    start_us: StrictInt
    end_us: StrictInt
    replacement_path: StrictStr
    evidence: list[ContinuityEvidencePayload] = []
    mechanical_facts: list[MechanicalFactPayload] = []
    observations: list[ContinuityObservationPayload] = []
    constraints: list[ContinuityConstraintPayload] = []
    review_targets: list[ReviewTargetPayload] = []


class RangeContinuityBriefStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: StrictInt
    briefs: list[RangeContinuityBriefPayload]


def _state_payload(state: RangeContinuityBriefState) -> RangeContinuityBriefStatePayload:
    return RangeContinuityBriefStatePayload.model_validate(state.to_dict())


def _brief_payload(brief: RangeContinuityBrief) -> RangeContinuityBriefPayload:
    return RangeContinuityBriefPayload.model_validate(brief.to_dict())


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, ContinuityBriefNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Continuity brief not found")
    if isinstance(exc, ContinuityBriefError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Continuity brief operation failed")


@router.get("/{project_id}/continuity-briefs", response_model=RangeContinuityBriefStatePayload)
def list_continuity_briefs(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> RangeContinuityBriefStatePayload:
    try:
        store.load_project(project_id)
        return _state_payload(RangeContinuityBriefStore(store).load(project_id))
    except (ProjectNotFound, ContinuityBriefError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/continuity-briefs/{edit_id}", response_model=RangeContinuityBriefPayload)
def get_continuity_brief(
    project_id: str,
    edit_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> RangeContinuityBriefPayload:
    try:
        store.load_project(project_id)
        brief = RangeContinuityBriefStore(store).load(project_id).get(edit_id)
        return _brief_payload(brief)
    except (ProjectNotFound, ContinuityBriefError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.put("/{project_id}/continuity-briefs/{edit_id}", response_model=RangeContinuityBriefStatePayload)
def put_continuity_brief(
    project_id: str,
    edit_id: str,
    request: RangeContinuityBriefPayload,
    store: ProjectStore = Depends(get_project_store),
) -> RangeContinuityBriefStatePayload:
    try:
        store.load_project(project_id)
        if request.edit_id != edit_id:
            raise ContinuityBriefError("URL edit_id must exactly match brief edit_id")
        brief = RangeContinuityBrief.from_dict(request.model_dump())
        return _state_payload(RangeContinuityBriefStore(store).upsert(project_id, brief))
    except (ProjectNotFound, ContinuityBriefError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.delete("/{project_id}/continuity-briefs/{edit_id}", response_model=RangeContinuityBriefStatePayload)
def delete_continuity_brief(
    project_id: str,
    edit_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> RangeContinuityBriefStatePayload:
    try:
        store.load_project(project_id)
        return _state_payload(RangeContinuityBriefStore(store).remove(project_id, edit_id))
    except (ProjectNotFound, ContinuityBriefError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
