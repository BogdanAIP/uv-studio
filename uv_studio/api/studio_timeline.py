"""Studio v2 timeline HTTP projection over the shared command service."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.capability_execution import get_local_ffmpeg_adapter
from uv_studio.api.projects import ProjectReferencePayload, get_project_store
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import CapabilityToolFailed, CapabilityToolUnavailable
from uv_studio.editor.studio_mlt import StudioMLTError, StudioMLTTimelineAdapter
from uv_studio.editor.studio_render import StudioRenderError, StudioTimelineRenderService
from uv_studio.editor.timeline_commands import (
    AddClipCommand,
    CreateTrackCommand,
    MoveClipCommand,
    RemoveClipCommand,
    TimelineCommandError,
    TimelineCommandService,
    TrimClipCommand,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.projects.timeline import TimelineError, TimelineStore

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Studio Timeline"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimelineClipPayload(_StrictModel):
    clip_id: str
    reference_id: str
    timeline_start_us: int
    source_start_us: int
    duration_us: int
    enabled: bool
    muted: bool


class TimelineTrackPayload(_StrictModel):
    track_id: str
    kind: Literal["video", "audio"]
    title: str
    enabled: bool
    muted: bool
    clips: list[TimelineClipPayload]


class TimelinePayload(_StrictModel):
    schema_version: int
    timeline_id: str
    tracks: list[TimelineTrackPayload]


class CreateTrackPayload(_StrictModel):
    command: Literal["create_track"]
    kind: Literal["video", "audio"]
    title: str | None = Field(default=None, min_length=1, max_length=200)
    track_id: str | None = Field(default=None, min_length=1, max_length=128)


class AddClipPayload(_StrictModel):
    command: Literal["add_clip"]
    track_id: str = Field(min_length=1, max_length=128)
    reference_id: str = Field(min_length=1, max_length=128)
    timeline_start_us: int = Field(ge=0)
    source_start_us: int = Field(default=0, ge=0)
    duration_us: int = Field(gt=0)
    clip_id: str | None = Field(default=None, min_length=1, max_length=128)


class MoveClipPayload(_StrictModel):
    command: Literal["move_clip"]
    clip_id: str = Field(min_length=1, max_length=128)
    timeline_start_us: int = Field(ge=0)


class TrimClipPayload(_StrictModel):
    command: Literal["trim_clip"]
    clip_id: str = Field(min_length=1, max_length=128)
    source_start_us: int = Field(ge=0)
    duration_us: int = Field(gt=0)


class RemoveClipPayload(_StrictModel):
    command: Literal["remove_clip"]
    clip_id: str = Field(min_length=1, max_length=128)


TimelineCommandPayload = Annotated[
    Union[
        CreateTrackPayload,
        AddClipPayload,
        MoveClipPayload,
        TrimClipPayload,
        RemoveClipPayload,
    ],
    Field(discriminator="command"),
]


class TimelineCommandResultPayload(_StrictModel):
    command: str
    track_id: str | None = None
    clip_id: str | None = None
    timeline: TimelinePayload


class MLTClipProjectionPayload(_StrictModel):
    track_id: str
    clip_id: str
    reference_id: str
    media_kind: str
    timeline_start_frame: int
    source_in_frame: int
    source_out_frame: int
    duration_frames: int
    enabled: bool


class MLTTrackProjectionPayload(_StrictModel):
    track_id: str
    kind: Literal["video", "audio"]
    enabled: bool
    muted: bool
    clips: list[MLTClipProjectionPayload]


class MLTProjectionPayload(_StrictModel):
    adapter_id: Literal["mlt"]
    timeline_id: str
    frame_rate: str
    width: int
    height: int
    duration_us: int
    duration_frames: int
    exact_boundaries: bool
    max_boundary_error_us: int
    tracks: list[MLTTrackProjectionPayload]
    runtime_available: bool


class StudioRenderPayload(_StrictModel):
    artifact: ProjectReferencePayload
    timeline_revision_sha256: str
    video_track_id: str
    audio_track_id: str | None
    duration_us: int


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, (TimelineCommandError, TimelineError, StudioMLTError, StudioRenderError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, CapabilityToolUnavailable):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local FFmpeg export tooling is unavailable in this installation",
        )
    if isinstance(exc, CapabilityToolFailed):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Studio timeline operation failed",
    )


@router.get("/{project_id}/studio/timeline", response_model=TimelinePayload)
def get_studio_timeline(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> TimelinePayload:
    try:
        timeline = TimelineStore(store).load(project_id, validate_references=True)
        return TimelinePayload.model_validate(timeline.to_dict())
    except (ProjectNotFound, TimelineError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/studio/timeline/engine", response_model=MLTProjectionPayload)
def get_studio_timeline_engine(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> MLTProjectionPayload:
    """Return a bounded MLT projection summary without exposing resolved host paths."""

    try:
        summary = StudioMLTTimelineAdapter(store).project_summary(project_id)
        return MLTProjectionPayload.model_validate(summary)
    except (ProjectNotFound, TimelineError, StudioMLTError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.post("/{project_id}/studio/timeline/render", response_model=StudioRenderPayload)
def render_studio_timeline(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    ffmpeg: LocalFFmpegAdapter = Depends(get_local_ffmpeg_adapter),
) -> StudioRenderPayload:
    """Render the bounded first Studio timeline path and register a project export."""

    try:
        result = StudioTimelineRenderService(store, ffmpeg).render(project_id)
        return StudioRenderPayload.model_validate(result.to_dict())
    except (
        ProjectNotFound,
        TimelineError,
        StudioMLTError,
        StudioRenderError,
        CapabilityToolUnavailable,
        CapabilityToolFailed,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


@router.post(
    "/{project_id}/studio/timeline/commands",
    response_model=TimelineCommandResultPayload,
    status_code=status.HTTP_201_CREATED,
)
def execute_studio_timeline_command(
    project_id: str,
    payload: TimelineCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> TimelineCommandResultPayload:
    service = TimelineCommandService(store)
    try:
        if isinstance(payload, CreateTrackPayload):
            result = service.create_track(
                project_id,
                CreateTrackCommand(kind=payload.kind, title=payload.title, track_id=payload.track_id),
            )
        elif isinstance(payload, AddClipPayload):
            result = service.add_clip(
                project_id,
                AddClipCommand(
                    track_id=payload.track_id,
                    reference_id=payload.reference_id,
                    timeline_start_us=payload.timeline_start_us,
                    source_start_us=payload.source_start_us,
                    duration_us=payload.duration_us,
                    clip_id=payload.clip_id,
                ),
            )
        elif isinstance(payload, MoveClipPayload):
            result = service.move_clip(
                project_id,
                MoveClipCommand(
                    clip_id=payload.clip_id,
                    timeline_start_us=payload.timeline_start_us,
                ),
            )
        elif isinstance(payload, TrimClipPayload):
            result = service.trim_clip(
                project_id,
                TrimClipCommand(
                    clip_id=payload.clip_id,
                    source_start_us=payload.source_start_us,
                    duration_us=payload.duration_us,
                ),
            )
        elif isinstance(payload, RemoveClipPayload):
            result = service.remove_clip(project_id, RemoveClipCommand(clip_id=payload.clip_id))
        else:  # pragma: no cover - discriminated union owns this invariant
            raise TimelineCommandError("unsupported Studio timeline command")
        return TimelineCommandResultPayload.model_validate(result.to_dict())
    except (ProjectNotFound, TimelineCommandError, TimelineError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
