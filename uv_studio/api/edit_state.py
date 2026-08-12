"""UV-owned HTTP API for non-destructive accepted range-edit decisions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    EditStateError,
    EditStateNotFound,
    ProjectStore,
    RangeEditState,
    RangeEditStateStore,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Edit State"])


class AcceptedRangeEditPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edit_id: str
    source_path: str
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    replacement_path: str


class RangeEditStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    edits: list[AcceptedRangeEditPayload]


def _payload(state: RangeEditState) -> RangeEditStatePayload:
    return RangeEditStatePayload.model_validate(state.to_dict())


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, EditStateNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edit decision not found")
    if isinstance(exc, EditStateError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Edit-state operation failed")


@router.get("/{project_id}/edits", response_model=RangeEditStatePayload)
def get_edit_state(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> RangeEditStatePayload:
    try:
        store.load_project(project_id)
        return _payload(RangeEditStateStore(store).load(project_id))
    except (ProjectNotFound, EditStateError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.delete("/{project_id}/edits/{edit_id}", response_model=RangeEditStatePayload)
def remove_edit(
    project_id: str,
    edit_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> RangeEditStatePayload:
    try:
        store.load_project(project_id)
        return _payload(RangeEditStateStore(store).remove(project_id, edit_id))
    except (ProjectNotFound, EditStateError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
