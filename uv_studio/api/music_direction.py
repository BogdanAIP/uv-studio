"""Semantic API boundary for Stage 7 Music Director and rhythm audit."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.music_direction import (
    DEFAULT_RHYTHM_AUDIT_TOLERANCE_US,
    MAX_MUSIC_SHOTS,
    MAX_RHYTHM_AUDIT_TOLERANCE_US,
    MAX_SYNC_MARKERS_PER_SHOT,
    MusicDirectionError,
    MusicDirectionStore,
    MusicShotPlan,
)
from uv_studio.projects.music_map import MusicMapError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Music Director"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MusicShotPlanPayload(_StrictModel):
    shot_id: str = Field(min_length=1, max_length=128)
    order: int = Field(ge=0, le=MAX_MUSIC_SHOTS - 1)
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    intent: str = Field(min_length=1, max_length=4000)
    sync_marker_ids: list[str] = Field(default_factory=list, max_length=MAX_SYNC_MARKERS_PER_SHOT)
    transition_out: Literal["cut", "dissolve", "fade", "match_cut", "other"] = "cut"


class SetMusicDirectionPayload(_StrictModel):
    command: Literal["set_music_direction"]
    music_map_revision_sha256: str = Field(min_length=64, max_length=64)
    shots: list[MusicShotPlanPayload] = Field(min_length=1, max_length=MAX_MUSIC_SHOTS)


class ClearMusicDirectionPayload(_StrictModel):
    command: Literal["clear_music_direction"]


MusicDirectionCommandPayload = Annotated[
    Union[SetMusicDirectionPayload, ClearMusicDirectionPayload],
    Field(discriminator="command"),
]


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, (MusicDirectionError, MusicMapError, ProjectValidationError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=500, detail="Music Director command failed")


@router.get("/{project_id}/music-direction")
def get_music_direction(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        state = MusicDirectionStore(store).load(project_id, validate_current=True)
        return {"music_direction": None if state is None else state.to_dict()}
    except (
        ProjectNotFound,
        MusicDirectionError,
        MusicMapError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/music-direction/commands", status_code=status.HTTP_201_CREATED)
def execute_music_direction_command(
    project_id: str,
    payload: MusicDirectionCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    service = MusicDirectionStore(store)
    try:
        store.load_project(project_id)
        if isinstance(payload, SetMusicDirectionPayload):
            value = service.set_direction(
                project_id,
                music_map_revision_sha256=payload.music_map_revision_sha256,
                shots=tuple(
                    MusicShotPlan(
                        shot_id=item.shot_id,
                        order=item.order,
                        start_us=item.start_us,
                        end_us=item.end_us,
                        intent=item.intent,
                        sync_marker_ids=tuple(item.sync_marker_ids),
                        transition_out=item.transition_out,
                    )
                    for item in payload.shots
                ),
            )
            return {"command": payload.command, "payload": value.to_dict()}
        if isinstance(payload, ClearMusicDirectionPayload):
            service.clear(project_id)
            return {"command": payload.command, "payload": None}
        raise MusicDirectionError("unsupported Music Director command")
    except (
        ProjectNotFound,
        MusicDirectionError,
        MusicMapError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/music-direction/rhythm-audit")
def get_music_rhythm_audit(
    project_id: str,
    tolerance_us: int = Query(
        default=DEFAULT_RHYTHM_AUDIT_TOLERANCE_US,
        ge=0,
        le=MAX_RHYTHM_AUDIT_TOLERANCE_US,
    ),
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        store.load_project(project_id)
        return MusicDirectionStore(store).rhythm_audit(
            project_id, tolerance_us=tolerance_us
        )
    except (
        ProjectNotFound,
        MusicDirectionError,
        MusicMapError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
