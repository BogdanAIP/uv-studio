"""Safe project-owned prepared speech audio upload and browser delivery."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from uv_studio.api.projects import ProjectReferencePayload, get_project_store
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.builtin import build_builtin_capability_registry
from uv_studio.capabilities.execution import (
    CapabilityExecutionError,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.prepared_audio import (
    PreparedAudioError,
    PreparedAudioNotFound,
    ProjectPreparedAudioStore,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Prepared Audio"])
MAX_PREPARED_AUDIO_UPLOAD_BYTES = 20 * 1024**3
_MEDIA_PROBE_OFFER_ID = "local_ffmpeg.media_probe"

PreparedAudioProbe = Callable[[ProjectStore, str, str], dict[str, Any]]


def _default_prepared_audio_probe(
    store: ProjectStore,
    project_id: str,
    relative_path: str,
) -> dict[str, Any]:
    registry = build_builtin_capability_registry()
    offer = registry.get_offer(_MEDIA_PROBE_OFFER_ID)
    result = LocalFFmpegAdapter(store).execute(
        project_id=project_id,
        offer=offer,
        payload={"path": relative_path},
    )
    return dict(result.output)


def get_prepared_audio_probe() -> PreparedAudioProbe:
    return _default_prepared_audio_probe


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, PreparedAudioNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prepared audio not found")
    if isinstance(exc, (PreparedAudioError, ProjectValidationError, InvalidCapabilityInput)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, (CapabilityToolUnavailable, UnsupportedCapabilityExecution)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local audio inspection is unavailable in this installation",
        )
    if isinstance(exc, CapabilityToolFailed):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded audio could not be inspected",
        )
    if isinstance(exc, (CapabilityExecutionError, ProjectStoreError)):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Prepared audio operation failed",
    )


def _reference_payload(reference: ProjectReference) -> ProjectReferencePayload:
    return ProjectReferencePayload.model_validate(reference.to_dict())


def _audio_stream(probe: dict[str, Any]) -> dict[str, Any]:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        return {}
    for item in streams:
        if isinstance(item, dict) and item.get("codec_type") == "audio":
            return item
    return {}


def _portable_audio_metadata(
    *,
    original_name: str,
    request_content_type: str | None,
    size_bytes: int,
    sha256: str,
    origin: str,
    probe: dict[str, Any],
) -> dict[str, Any]:
    if probe.get("has_audio") is not True:
        raise PreparedAudioError("uploaded prepared speech does not contain an audio stream")
    if probe.get("has_video") is True:
        raise PreparedAudioError("uploaded prepared speech must be audio-only")
    duration_us = probe.get("duration_us")
    if isinstance(duration_us, bool) or not isinstance(duration_us, int) or duration_us <= 0:
        raise PreparedAudioError("uploaded prepared speech must have a known positive duration")

    content_type = (
        request_content_type.split(";", 1)[0].strip().lower()
        if isinstance(request_content_type, str)
        else ""
    )
    if not content_type.startswith("audio/"):
        guessed, _encoding = mimetypes.guess_type(original_name)
        content_type = guessed if isinstance(guessed, str) and guessed.startswith("audio/") else "application/octet-stream"

    stream = _audio_stream(probe)
    metadata: dict[str, Any] = {
        "original_name": original_name,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "duration_us": duration_us,
        "has_audio": True,
        "has_video": False,
        "origin": origin,
    }
    optional_text = {
        "format_name": probe.get("format_name"),
        "audio_codec": stream.get("codec_name"),
        "channel_layout": stream.get("channel_layout"),
        "sample_fmt": stream.get("sample_fmt"),
    }
    for key, value in optional_text.items():
        if isinstance(value, str) and value:
            metadata[key] = value
    channels = stream.get("channels")
    if isinstance(channels, int) and not isinstance(channels, bool) and channels > 0:
        metadata["channels"] = channels
    sample_rate = stream.get("sample_rate")
    if isinstance(sample_rate, int) and not isinstance(sample_rate, bool) and sample_rate > 0:
        metadata["sample_rate"] = sample_rate
    elif isinstance(sample_rate, str) and sample_rate.isdigit() and int(sample_rate) > 0:
        metadata["sample_rate"] = int(sample_rate)
    return metadata


@router.post(
    "/{project_id}/prepared-audio",
    response_model=ProjectReferencePayload,
    status_code=status.HTTP_201_CREATED,
)
async def upload_prepared_audio(
    project_id: str,
    request: Request,
    filename: str = Query(min_length=1, max_length=1024),
    origin: Literal["imported", "recorded"] = Query(default="imported"),
    store: ProjectStore = Depends(get_project_store),
    probe_media: PreparedAudioProbe = Depends(get_prepared_audio_probe),
) -> ProjectReferencePayload:
    """Stream a user-provided speech take into project assets and register after probing."""

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_PREPARED_AUDIO_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Prepared audio is too large",
                )
        except ValueError:
            pass

    media_store = ProjectPreparedAudioStore(store)
    try:
        allocation = media_store.allocate(project_id, filename)
    except (ProjectNotFound, PreparedAudioError, ProjectStoreError) as exc:
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
                if written > MAX_PREPARED_AUDIO_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Prepared audio is too large",
                    )
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if written == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prepared audio body is empty",
            )

        os.replace(temporary, allocation.absolute_path)
        final_written = True
        probe = probe_media(store, project_id, allocation.relative_path)
        metadata = _portable_audio_metadata(
            original_name=allocation.original_name,
            request_content_type=request.headers.get("content-type"),
            size_bytes=written,
            sha256=digest.hexdigest(),
            origin=origin,
            probe=probe,
        )
        project = media_store.register(project_id, allocation, metadata=metadata)
        registered = next(item for item in project.artifacts if item.id == allocation.audio_id)
        return _reference_payload(registered)
    except HTTPException:
        raise
    except (
        ProjectNotFound,
        PreparedAudioError,
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
                registered = any(item.id == allocation.audio_id for item in project.artifacts)
            except Exception:
                registered = False
            if not registered:
                allocation.absolute_path.unlink(missing_ok=True)


@router.get(
    "/{project_id}/prepared-audio/{audio_id}",
    response_model=ProjectReferencePayload,
)
def get_prepared_audio(
    project_id: str,
    audio_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectReferencePayload:
    try:
        return _reference_payload(ProjectPreparedAudioStore(store).get(project_id, audio_id))
    except (ProjectNotFound, PreparedAudioNotFound, PreparedAudioError, ProjectStoreError) as exc:
        raise _translate(exc) from exc


@router.get("/{project_id}/prepared-audio/{audio_id}/media", response_class=FileResponse)
def stream_prepared_audio(
    project_id: str,
    audio_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    """Deliver only a registered prepared speech asset; byte ranges are supported."""

    try:
        reference, path = ProjectPreparedAudioStore(store).resolve(project_id, audio_id)
    except (ProjectNotFound, PreparedAudioNotFound, PreparedAudioError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    metadata = reference.metadata
    media_type = metadata.get("content_type")
    if not isinstance(media_type, str) or not media_type.startswith("audio/"):
        guessed, _encoding = mimetypes.guess_type(path.name)
        media_type = guessed if isinstance(guessed, str) and guessed.startswith("audio/") else "application/octet-stream"
    original_name = metadata.get("original_name")
    if not isinstance(original_name, str) or not original_name:
        original_name = path.name
    return FileResponse(
        path=path,
        media_type=media_type,
        filename=original_name,
        content_disposition_type="inline",
    )
