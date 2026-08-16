"""Semantic API for composition-first Stage 8 recipe input workspaces."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects.stage8_workspace import (
    Stage8WorkspaceError,
    get_stage8_workspace,
    save_stage8_workspace,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Stage 8 Workspace"])


class Stage8WorkspaceSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str = Field(default="", max_length=20_000)
    script: str = Field(default="", max_length=200_000)
    source_ids: list[str] = Field(default_factory=list, max_length=200)


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, Stage8WorkspaceError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stage 8 workspace operation failed")


@router.get("/{project_id}/stage8/workspace")
def get_project_stage8_workspace(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object | None]:
    try:
        workspace = get_stage8_workspace(store, project_id)
    except (ProjectNotFound, Stage8WorkspaceError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    return {"workspace": None if workspace is None else workspace.to_dict()}


@router.put("/{project_id}/stage8/workspace")
def put_project_stage8_workspace(
    project_id: str,
    request: Stage8WorkspaceSaveRequest,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, object]:
    try:
        workspace = save_stage8_workspace(
            store,
            project_id,
            brief=request.brief,
            script=request.script,
            source_ids=request.source_ids,
        )
    except (ProjectNotFound, Stage8WorkspaceError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    return {"workspace": workspace.to_dict()}
