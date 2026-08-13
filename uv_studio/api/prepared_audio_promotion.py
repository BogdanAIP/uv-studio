"""Promote an existing project-owned audio artifact into canonical prepared speech."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from uv_studio.api.prepared_audio import (
    PreparedAudioProbe,
    _portable_audio_metadata,
    _reference_payload,
    _translate,
    get_prepared_audio_probe,
)
from uv_studio.api.projects import ProjectReferencePayload, get_project_store
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.prepared_audio import PreparedAudioError, ProjectPreparedAudioStore
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Prepared Audio"])
_COPY_CHUNK_BYTES = 1024 * 1024


@router.post(
    "/{project_id}/prepared-audio/from-artifact/{artifact_id}",
    response_model=ProjectReferencePayload,
    status_code=status.HTTP_201_CREATED,
)
def promote_audio_artifact_to_prepared_speech(
    project_id: str,
    artifact_id: str,
    origin: Literal["tts", "imported", "recorded"] = Query(default="tts"),
    store: ProjectStore = Depends(get_project_store),
    probe_media: PreparedAudioProbe = Depends(get_prepared_audio_probe),
) -> ProjectReferencePayload:
    """Copy one bounded project audio artifact into the prepared-speech asset boundary.

    No host path, digest, duration or stream metadata is accepted from the caller.
    The copied bytes are re-hashed and re-probed before registration.
    """

    try:
        project = store.load_project(project_id)
    except (ProjectNotFound, ProjectStoreError) as exc:
        raise _translate(exc) from exc

    source_ref = next((item for item in project.artifacts if item.id == artifact_id), None)
    if source_ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio artifact not found")
    if source_ref.kind != "audio":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only an audio artifact can be promoted to prepared speech",
        )
    if not source_ref.path.startswith("artifacts/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prepared-audio promotion accepts only project artifacts/ inputs",
        )

    try:
        source_path = store.resolve_project_file(
            project_id,
            source_ref.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    if not source_path.is_file() or source_path.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Audio artifact must be a regular project file",
        )

    original_name = source_ref.metadata.get("original_name")
    if not isinstance(original_name, str) or not original_name.strip():
        original_name = source_path.name
    media_store = ProjectPreparedAudioStore(store)
    try:
        allocation = media_store.allocate(project_id, original_name)
    except (ProjectNotFound, PreparedAudioError, ProjectStoreError) as exc:
        raise _translate(exc) from exc

    temporary = allocation.absolute_path.with_name(
        f".{allocation.absolute_path.name}.{uuid.uuid4().hex}.promote"
    )
    final_written = False
    digest = hashlib.sha256()
    size_bytes = 0
    try:
        before = source_path.stat()
        with source_path.open("rb") as input_handle, temporary.open("xb") as output_handle:
            while chunk := input_handle.read(_COPY_CHUNK_BYTES):
                digest.update(chunk)
                size_bytes += len(chunk)
                output_handle.write(chunk)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        after = source_path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise PreparedAudioError("source audio artifact changed while being promoted")
        if size_bytes <= 0:
            raise PreparedAudioError("source audio artifact is empty")
        os.replace(temporary, allocation.absolute_path)
        final_written = True

        probe = probe_media(store, project_id, allocation.relative_path)
        source_content_type = source_ref.metadata.get("content_type")
        if not isinstance(source_content_type, str):
            guessed, _encoding = mimetypes.guess_type(original_name)
            source_content_type = guessed
        metadata = _portable_audio_metadata(
            original_name=allocation.original_name,
            request_content_type=source_content_type,
            size_bytes=size_bytes,
            sha256=digest.hexdigest(),
            origin=origin,
            probe=probe,
        )
        metadata["promoted_from_artifact_id"] = source_ref.id
        registered_project = media_store.register(
            project_id,
            allocation,
            metadata=metadata,
        )
        registered = next(
            item for item in registered_project.artifacts if item.id == allocation.audio_id
        )
        return _reference_payload(registered)
    except HTTPException:
        raise
    except (PreparedAudioError, ProjectValidationError, ProjectStoreError) as exc:
        raise _translate(exc) from exc
    finally:
        temporary.unlink(missing_ok=True)
        if final_written:
            try:
                current = store.load_project(project_id)
                registered = any(item.id == allocation.audio_id for item in current.artifacts)
            except Exception:
                registered = False
            if not registered:
                allocation.absolute_path.unlink(missing_ok=True)
