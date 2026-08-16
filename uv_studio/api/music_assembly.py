"""Semantic API boundary for revision-bound Stage 7 visual assembly."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.music_assembly import (
    MAX_MUSIC_ASSEMBLY_BINDINGS,
    MusicAssemblyError,
    MusicAssemblyStore,
    MusicVisualAssignment,
)
from uv_studio.projects.music_direction import MusicDirectionError
from uv_studio.projects.music_map import MusicMapError
from uv_studio.projects.source_media import SourceMediaError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Music Assembly"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MusicVisualAssignmentPayload(_StrictModel):
    shot_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128)
    source_start_us: int = Field(default=0, ge=0)


class SetMusicAssemblyPayload(_StrictModel):
    command: Literal["set_music_assembly"]
    music_direction_revision_sha256: str = Field(min_length=64, max_length=64)
    assignments: list[MusicVisualAssignmentPayload] = Field(
        min_length=1, max_length=MAX_MUSIC_ASSEMBLY_BINDINGS
    )


class ClearMusicAssemblyPayload(_StrictModel):
    command: Literal["clear_music_assembly"]


MusicAssemblyCommandPayload = Annotated[
    Union[SetMusicAssemblyPayload, ClearMusicAssemblyPayload],
    Field(discriminator="command"),
]


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(
        exc,
        (
            MusicAssemblyError,
            MusicDirectionError,
            MusicMapError,
            SourceMediaError,
            ProjectValidationError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=500, detail="Music assembly command failed")


@router.get("/{project_id}/music-assembly")
def get_music_assembly(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        state = MusicAssemblyStore(store).load(project_id, validate_current=True)
        return {"music_assembly": None if state is None else state.to_dict()}
    except (
        ProjectNotFound,
        MusicAssemblyError,
        MusicDirectionError,
        MusicMapError,
        SourceMediaError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/music-assembly/commands", status_code=status.HTTP_201_CREATED)
def execute_music_assembly_command(
    project_id: str,
    payload: MusicAssemblyCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    service = MusicAssemblyStore(store)
    try:
        store.load_project(project_id)
        if isinstance(payload, SetMusicAssemblyPayload):
            state = service.set_assembly(
                project_id,
                music_direction_revision_sha256=payload.music_direction_revision_sha256,
                assignments=tuple(
                    MusicVisualAssignment(
                        shot_id=item.shot_id,
                        source_id=item.source_id,
                        source_start_us=item.source_start_us,
                    )
                    for item in payload.assignments
                ),
            )
            return {"command": payload.command, "payload": state.to_dict()}
        if isinstance(payload, ClearMusicAssemblyPayload):
            service.clear(project_id)
            return {"command": payload.command, "payload": None}
        raise MusicAssemblyError("unsupported music assembly command")
    except (
        ProjectNotFound,
        MusicAssemblyError,
        MusicDirectionError,
        MusicMapError,
        SourceMediaError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
