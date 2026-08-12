"""UV Studio-owned semantic editor command HTTP boundary."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import ProjectReferencePayload, get_project_store
from uv_studio.editor.commands import EditorCommandError, EditorCommandService, SelectRangeCommand
from uv_studio.projects.continuity_brief import (
    ContinuityBriefError,
    RangeContinuityBriefStore,
)
from uv_studio.projects.edit_state import EditStateError, RangeEditStateStore
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.source_media import SourceMediaError, SourceMediaNotFound
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Editor"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SelectRangeCommandPayload(_StrictModel):
    command: Literal["select_range"]
    source_id: str = Field(min_length=1, max_length=128)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    change_request: str = Field(min_length=1, max_length=4000)
    context_before_us: int = Field(default=5_000_000, ge=0, le=30_000_000)
    context_after_us: int = Field(default=5_000_000, ge=0, le=30_000_000)


EditorCommandPayload = Annotated[
    Union[SelectRangeCommandPayload],
    Field(discriminator="command"),
]


class SelectRangeCommandResultPayload(_StrictModel):
    command: Literal["select_range"]
    source_id: str
    edit_id: str
    resolved_range: dict
    brief: dict


class EditorStatePayload(_StrictModel):
    sources: list[ProjectReferencePayload]
    briefs: list[dict]
    accepted_edits: list[dict]


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, SourceMediaNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source media not found")
    if isinstance(
        exc,
        (
            EditorCommandError,
            SourceMediaError,
            ContinuityBriefError,
            EditStateError,
            ProjectValidationError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Editor command failed",
    )


@router.post(
    "/{project_id}/editor/commands",
    response_model=SelectRangeCommandResultPayload,
    status_code=status.HTTP_201_CREATED,
)
def execute_editor_command(
    project_id: str,
    payload: EditorCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> SelectRangeCommandResultPayload:
    """Execute one semantic editor mutation through the shared product boundary."""

    try:
        if isinstance(payload, SelectRangeCommandPayload):
            result = EditorCommandService(store).select_range(
                project_id,
                SelectRangeCommand(
                    source_id=payload.source_id,
                    start_us=payload.start_us,
                    end_us=payload.end_us,
                    change_request=payload.change_request,
                    context_before_us=payload.context_before_us,
                    context_after_us=payload.context_after_us,
                ),
            )
            return SelectRangeCommandResultPayload.model_validate(result.to_dict())
        raise EditorCommandError("unsupported editor command")
    except (
        ProjectNotFound,
        SourceMediaNotFound,
        EditorCommandError,
        SourceMediaError,
        ContinuityBriefError,
        EditStateError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/editor/state", response_model=EditorStatePayload)
def get_editor_state(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> EditorStatePayload:
    """Return canonical state needed to reconstruct the Stage 4C editor workspace."""

    try:
        project = store.load_project(project_id)
        briefs = RangeContinuityBriefStore(store).load(project_id)
        accepted = RangeEditStateStore(store).load(project_id)
        return EditorStatePayload(
            sources=[
                ProjectReferencePayload.model_validate(reference.to_dict())
                for reference in project.sources
                if reference.kind == "video"
            ],
            briefs=[brief.to_dict() for brief in briefs.briefs],
            accepted_edits=[edit.to_dict() for edit in accepted.edits],
        )
    except (
        ProjectNotFound,
        ContinuityBriefError,
        EditStateError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
