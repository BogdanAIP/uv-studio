"""HTTP projection of the shared Project Unit of Work history authority."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from uv_studio.api.project_common import get_project_store
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.projects.transactions import (
    NothingToRedo,
    NothingToUndo,
    ProjectTransactionConflict,
    ProjectTransactionError,
    ProjectTransactionRecoveryError,
    ProjectUnitOfWork,
)

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Transactions"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectTransactionEntryPayload(_StrictModel):
    transaction_id: str
    command: str
    created_at: str
    changed_paths: list[str]


class ProjectHistoryPayload(_StrictModel):
    schema_version: int
    cursor: int
    can_undo: bool
    can_redo: bool
    current_transaction_id: str | None
    entries: list[ProjectTransactionEntryPayload]


class ProjectTransactionOperationPayload(_StrictModel):
    operation_id: str
    operation: str
    transaction_id: str
    history: ProjectHistoryPayload


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, (NothingToUndo, NothingToRedo, ProjectTransactionConflict)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ProjectTransactionError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    if isinstance(exc, (ProjectTransactionRecoveryError, ProjectStoreError)):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Project transaction operation failed",
    )


@router.get("/{project_id}/studio/history", response_model=ProjectHistoryPayload)
def get_project_history(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectHistoryPayload:
    try:
        return ProjectHistoryPayload.model_validate(ProjectUnitOfWork(store).history(project_id).to_dict())
    except (ProjectNotFound, ProjectTransactionError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/studio/history/undo", response_model=ProjectTransactionOperationPayload)
def undo_project_transaction(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectTransactionOperationPayload:
    try:
        result = ProjectUnitOfWork(store).undo(project_id)
        return ProjectTransactionOperationPayload.model_validate(result.to_dict())
    except (ProjectNotFound, ProjectTransactionError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/studio/history/redo", response_model=ProjectTransactionOperationPayload)
def redo_project_transaction(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectTransactionOperationPayload:
    try:
        result = ProjectUnitOfWork(store).redo(project_id)
        return ProjectTransactionOperationPayload.model_validate(result.to_dict())
    except (ProjectNotFound, ProjectTransactionError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
