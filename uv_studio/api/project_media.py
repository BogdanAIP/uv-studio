"""Safe project-owned source-media upload and browser delivery."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from uv_studio.api.projects import ProjectReferencePayload, get_project_store
from uv_studio.capabilities.adapters.local_ffmpeg import LocalFFmpegAdapter
from uv_studio.capabilities.builtin import build_builtin_capability_registry
from uv_studio.capabilities.execution import (
    CapabilityExecutionError,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.source_media import (
    ProjectSourceMediaStore,
    SourceMediaError,
    SourceMediaNotFound,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Project Media"])
MAX_SOURCE_UPLOAD_BYTES = 100 * 1024**3
_SOURCE_MEDIA_OFFER_ID = "local_ffmpeg.media_probe"

SourceMediaProbe = Callable[[ProjectStore, str, str], dict[str, Any]]


def _default_source_media_probe(
    store: ProjectStore,
    project_id: str,
    relative_path: str,
) -> dict[str, Any]:
    registry = build_builtin_capability_registry()
    offer = registry.get_offer(_SOURCE_MEDIA_OFFER_ID)
    result = LocalFFmpegAdapter(store).execute(
        project_id=project_id,
        offer=offer,
        payload={"path": relative_path},
    )
    return dict(result.output)


def get_source_media_probe() -> SourceMediaProbe:
    """Dependency seam for deterministic API tests and the real FFprobe runtime."""

    return _default_source_media_probe


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, SourceMediaNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source media not found")
    if isinstance(exc, (SourceMediaError, ProjectValidationError, InvalidCapabilityInput)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, (CapabilityToolUnavailable, UnsupportedCapabilityExecution)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local media inspection is unavailable in this installation",
        )
    if isinstance(exc, CapabilityToolFailed):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded media could not be inspected",
        )
    if isinstance(exc, (CapabilityExecutionError, ProjectStoreError)):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Project media operation failed",
    )


def _reference_payload(reference: ProjectReference) -> ProjectReferencePayload:
    return ProjectReferencePayload.model_validate(reference.to_dict())


def _positive_duration(probe: dict[str, Any], *, media_kind: str) -> int:
    duration_us = probe.get("duration_us")
    if isinstance(duration_us, bool) or not isinstance(duration_us, int) or duration_us <= 0:
        stream = probe.get(media_kind)
        duration_us = stream.get("duration_us") if isinstance(stream, dict) else None
    if isinstance(duration_us, bool) or not isinstance(duration_us, int) or duration_us <= 0:
        raise SourceMediaError(f"uploaded {media_kind} must have a known positive duration")
    return duration_us


def _portable_probe_metadata(
    *,
    media_kind: str,
    original_name: str,
    request_content_type: str | None,
    size_bytes: int,
    sha256: str,
    probe: dict[str, Any],
) -> dict[str, Any]:
    if media_kind == "video":
        if probe.get("has_video") is not True:
            raise SourceMediaError("uploaded source does not contain a video stream")
        duration_us = _positive_duration(probe, media_kind="video")
        stream = probe.get("video") if isinstance(probe.get("video"), dict) else {}
        expected_prefix = "video/"
        metadata: dict[str, Any] = {
            "original_name": original_name,
            "content_type": "application/octet-stream",
            "size_bytes": size_bytes,
            "sha256": sha256,
            "duration_us": duration_us,
            "has_audio": probe.get("has_audio") is True,
        }
        optional = {
            "format_name": probe.get("format_name"),
            "video_codec": stream.get("codec"),
            "width": stream.get("width"),
            "height": stream.get("height"),
            "avg_frame_rate": stream.get("avg_frame_rate"),
        }
    elif media_kind == "audio":
        if probe.get("has_audio") is not True:
            raise SourceMediaError("uploaded source does not contain an audio stream")
        if probe.get("has_video") is True:
            raise SourceMediaError("uploaded audio source must not contain a video stream")
        duration_us = _positive_duration(probe, media_kind="audio")
        stream = probe.get("audio") if isinstance(probe.get("audio"), dict) else {}
        expected_prefix = "audio/"
        metadata = {
            "original_name": original_name,
            "content_type": "application/octet-stream",
            "size_bytes": size_bytes,
            "sha256": sha256,
            "duration_us": duration_us,
            "has_audio": True,
        }
        optional = {
            "format_name": probe.get("format_name"),
            "audio_codec": stream.get("codec"),
            "sample_rate": stream.get("sample_rate"),
            "channels": stream.get("channels"),
            "channel_layout": stream.get("channel_layout"),
        }
    else:  # pragma: no cover - internal invariant
        raise SourceMediaError(f"unsupported source media kind: {media_kind!r}")

    content_type = (
        request_content_type.split(";", 1)[0].strip().lower()
        if isinstance(request_content_type, str)
        else ""
    )
    if content_type.startswith(expected_prefix):
        metadata["content_type"] = content_type
    for key, value in optional.items():
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            metadata[key] = value
    return metadata


async def _upload_source(
    *,
    project_id: str,
    request: Request,
    filename: str,
    media_kind: str,
    store: ProjectStore,
    probe_media: SourceMediaProbe,
) -> ProjectReferencePayload:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_SOURCE_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Source media is too large",
                )
        except ValueError:
            pass

    media_store = ProjectSourceMediaStore(store)
    try:
        allocation = media_store.allocate(project_id, filename)
    except (ProjectNotFound, SourceMediaError, ProjectStoreError) as exc:
        raise _translate(exc) from exc

    temporary = allocation.absolute_path.with_name(
        f".{allocation.absolute_path.name}.{uuid.uuid4().hex}.upload"
    )
    written = 0
    digest = hashlib.sha256()
    final_written = False
    try:
        with temporary.open("xb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                written += len(chunk)
                if written > MAX_SOURCE_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Source media is too large",
                    )
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if written == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source media body is empty",
            )

        os.replace(temporary, allocation.absolute_path)
        final_written = True
        probe = probe_media(store, project_id, allocation.relative_path)
        metadata = _portable_probe_metadata(
            media_kind=media_kind,
            original_name=allocation.original_name,
            request_content_type=request.headers.get("content-type"),
            size_bytes=written,
            sha256=digest.hexdigest(),
            probe=probe,
        )
        project = media_store.register(
            project_id,
            allocation,
            metadata=metadata,
            media_kind=media_kind,
        )
        registered = next(item for item in project.sources if item.id == allocation.source_id)
        return _reference_payload(registered)
    except HTTPException:
        raise
    except (
        ProjectNotFound,
        SourceMediaError,
        ProjectValidationError,
        CapabilityExecutionError,
        ProjectStoreError,
    ) as exc:
        raise _translate(exc) from exc
    finally:
        temporary.unlink(missing_ok=True)
        if final_written:
            try:
                project = store.load_project(project_id)
                registered = any(item.id == allocation.source_id for item in project.sources)
            except Exception:
                registered = False
            if not registered:
                allocation.absolute_path.unlink(missing_ok=True)


@router.post(
    "/{project_id}/sources",
    response_model=ProjectReferencePayload,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source_media(
    project_id: str,
    request: Request,
    filename: str = Query(min_length=1, max_length=1024),
    store: ProjectStore = Depends(get_project_store),
    probe_media: SourceMediaProbe = Depends(get_source_media_probe),
) -> ProjectReferencePayload:
    """Stream one source video into the Project Store and register it after probing."""

    return await _upload_source(
        project_id=project_id,
        request=request,
        filename=filename,
        media_kind="video",
        store=store,
        probe_media=probe_media,
    )


@router.post(
    "/{project_id}/sources/audio",
    response_model=ProjectReferencePayload,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source_audio(
    project_id: str,
    request: Request,
    filename: str = Query(min_length=1, max_length=1024),
    store: ProjectStore = Depends(get_project_store),
    probe_media: SourceMediaProbe = Depends(get_source_media_probe),
) -> ProjectReferencePayload:
    """Stream one audio-only source into Project Store for music and other audio workflows."""

    return await _upload_source(
        project_id=project_id,
        request=request,
        filename=filename,
        media_kind="audio",
        store=store,
        probe_media=probe_media,
    )


@router.get(
    "/{project_id}/sources/audio/{source_id}",
    response_model=ProjectReferencePayload,
)
def get_audio_source(
    project_id: str,
    source_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectReferencePayload:
    try:
        return _reference_payload(
            ProjectSourceMediaStore(store).get(
                project_id, source_id, expected_kind="audio"
            )
        )
    except (ProjectNotFound, SourceMediaNotFound, SourceMediaError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/sources/audio/{source_id}/media", response_class=FileResponse)
def stream_audio_source(
    project_id: str,
    source_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    try:
        reference, path = ProjectSourceMediaStore(store).resolve(
            project_id, source_id, expected_kind="audio"
        )
    except (ProjectNotFound, SourceMediaNotFound, SourceMediaError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    return _source_file_response(reference, path)


@router.get(
    "/{project_id}/sources/{source_id}",
    response_model=ProjectReferencePayload,
)
def get_source_media(
    project_id: str,
    source_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectReferencePayload:
    try:
        return _reference_payload(ProjectSourceMediaStore(store).get(project_id, source_id))
    except (ProjectNotFound, SourceMediaNotFound, SourceMediaError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


def _source_file_response(reference: ProjectReference, path: Path) -> FileResponse:
    metadata = reference.metadata
    media_type = metadata.get("content_type")
    if not isinstance(media_type, str) or not media_type:
        media_type = "application/octet-stream"
    original_name = metadata.get("original_name")
    if not isinstance(original_name, str) or not original_name:
        original_name = path.name
    return FileResponse(
        path=path,
        media_type=media_type,
        filename=original_name,
        content_disposition_type="inline",
    )


@router.get("/{project_id}/sources/{source_id}/media", response_class=FileResponse)
def stream_source_media(
    project_id: str,
    source_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    """Deliver only a registered project video source; Starlette handles byte ranges."""

    try:
        reference, path = ProjectSourceMediaStore(store).resolve(project_id, source_id)
    except (ProjectNotFound, SourceMediaNotFound, SourceMediaError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    return _source_file_response(reference, path)


@router.get("/{project_id}/artifacts/{artifact_id}/media", response_class=FileResponse)
def stream_video_artifact(
    project_id: str,
    artifact_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    """Deliver only a registered project-owned video artifact for browser review."""

    try:
        project = store.load_project(project_id)
        reference = next(
            (
                item
                for item in project.artifacts
                if item.id == artifact_id and item.kind == "video"
            ),
            None,
        )
        if reference is None:
            raise HTTPException(status_code=404, detail="Video artifact not found")
        path = store.resolve_project_file(
            project_id,
            reference.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
    except HTTPException:
        raise
    except ProjectNotFound as exc:
        raise _translate(exc) from exc
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(status_code=422, detail="Video artifact is not safely resolvable") from exc

    if not path.is_file() or path.is_symlink():
        raise HTTPException(status_code=404, detail="Video artifact not found")

    metadata = reference.metadata
    media_type = metadata.get("content_type")
    if not isinstance(media_type, str) or not media_type.startswith("video/"):
        guessed, _encoding = mimetypes.guess_type(path.name)
        media_type = (
            guessed
            if isinstance(guessed, str) and guessed.startswith("video/")
            else "application/octet-stream"
        )
    original_name = metadata.get("original_name")
    if not isinstance(original_name, str) or not original_name:
        original_name = path.name
    return FileResponse(
        path=path,
        media_type=media_type,
        filename=original_name,
        content_disposition_type="inline",
    )
