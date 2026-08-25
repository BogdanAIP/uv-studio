"""Studio v2 HTTP boundary over canonical project/timeline services."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.capability_execution import get_local_ffmpeg_adapter
from uv_studio.api.project_common import (
    ProjectPayload,
    ProjectReferencePayload,
    get_project_store,
    project_payload,
)
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
from uv_studio.production.directions import (
    ProductionDirectionNotFound,
    get_production_direction,
    list_production_directions,
)
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import (
    ProjectAlreadyExists,
    ProjectNotFound,
    ProjectStore,
    ProjectStoreError,
)
from uv_studio.projects.timeline import TimelineError, TimelineStore

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Studio"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductionDirectionPayload(_StrictModel):
    direction_id: str
    title: str
    description: str
    primary_input_label: str
    workspace_sections: list[str]
    default_tools: list[str]
    featured: bool


class CreateStudioProjectPayload(_StrictModel):
    title: str = Field(min_length=1, max_length=500)
    direction_id: str = Field(min_length=1, max_length=128)


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
    if isinstance(exc, ProjectAlreadyExists):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project already exists")
    if isinstance(
        exc,
        (
            ProjectValidationError,
            ProductionDirectionNotFound,
            TimelineCommandError,
            TimelineError,
            StudioMLTError,
            StudioRenderError,
        ),
    ):
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
        detail="Studio operation failed",
    )


@router.get("/studio/directions", response_model=list[ProductionDirectionPayload])
def get_studio_production_directions() -> list[ProductionDirectionPayload]:
    """Return the product-level production directions available to new Studio projects."""

    return [
        ProductionDirectionPayload.model_validate(direction.to_dict())
        for direction in list_production_directions()
    ]


@router.post("/studio", response_model=ProjectPayload, status_code=status.HTTP_201_CREATED)
def create_studio_project(
    request: CreateStudioProjectPayload,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectPayload:
    """Create one modern Studio project with a validated Production Direction."""

    try:
        direction = get_production_direction(request.direction_id)
        project = store.create_project(
            title=request.title,
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions(direction.direction_id),
        )
        return project_payload(project)
    except (
        ProductionDirectionNotFound,
        ProjectValidationError,
        ProjectAlreadyExists,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc


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


@router.get("/{project_id}/studio/exports/{artifact_id}/media", response_class=FileResponse)
def stream_studio_export(
    project_id: str,
    artifact_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    """Stream only a registered Studio video export from the project ``exports`` root."""

    try:
        project = store.load_project(project_id)
        reference = next(
            (
                item
                for item in project.artifacts
                if item.id == artifact_id
                and item.kind == "video"
                and item.metadata.get("role") == "studio-export"
            ),
            None,
        )
        if reference is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio export not found")
        path = store.resolve_project_file(
            project_id,
            reference.path,
            must_exist=True,
            allowed_roots=("exports",),
        )
    except HTTPException:
        raise
    except (ProjectNotFound, ProjectValidationError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    if not path.is_file() or path.is_symlink():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio export not found")
    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=path.name,
        content_disposition_type="inline",
    )


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
