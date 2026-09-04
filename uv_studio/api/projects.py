"""Compatibility HTTP endpoints for canonical UV Studio projects.

Neutral project schemas/dependencies live in ``api.project_common`` so modern
Studio/media modules do not import the Recipe Registry/Product Orchestrator
merely to access Project Store services.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.background import BackgroundTask

from uv_studio.api.project_common import (
    ProjectPayload,
    ProjectReferencePayload,
    get_project_store,
    project_payload,
)
from uv_studio.projects.archive import ProjectArchiveError, export_project, import_project
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import (
    ProjectAlreadyExists,
    ProjectNotFound,
    ProjectStore,
    ProjectStoreError,
)

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Projects"])
MAX_ARCHIVE_UPLOAD_BYTES = 100 * 1024**3


class UpdateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=500)
    settings: dict[str, Any] | None = None
    extensions: dict[str, Any] | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "UpdateProjectRequest":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


def _translate_store_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, ProjectAlreadyExists):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project already exists")
    if isinstance(exc, (ProjectValidationError, ProjectArchiveError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Project operation failed")


def _temporary_archive_path(store: ProjectStore, *, prefix: str) -> Path:
    fd, raw_path = tempfile.mkstemp(
        prefix=prefix,
        suffix=".uvproj.zip",
        dir=store.root,
    )
    os.close(fd)
    path = Path(raw_path)
    path.unlink(missing_ok=True)
    return path


@router.get("", response_model=list[ProjectPayload])
def list_projects(store: ProjectStore = Depends(get_project_store)) -> list[ProjectPayload]:
    try:
        return [project_payload(item) for item in store.list_projects()]
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise _translate_store_error(exc) from exc


@router.post("/import", response_model=ProjectPayload, status_code=status.HTTP_201_CREATED)
async def import_project_archive(
    request: Request,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectPayload:
    """Stream one `.uvproj.zip` request body to disk, validate it, then import atomically.

    Legacy recipe IDs may remain unknown/uncreatable so old data is recoverable.
    Malformed or conflicting Studio identity is rejected by the Project Store
    staging boundary rather than being silently imported as a modern project.
    """
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_ARCHIVE_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Project archive is too large",
                )
        except ValueError:
            pass

    fd, raw_path = tempfile.mkstemp(
        prefix=".uv-upload-",
        suffix=".uvproj.zip",
        dir=store.root,
    )
    os.close(fd)
    upload_path = Path(raw_path)
    written = 0
    try:
        with upload_path.open("wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                written += len(chunk)
                if written > MAX_ARCHIVE_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Project archive is too large",
                    )
                output.write(chunk)
        if written == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project archive body is empty",
            )
        document = import_project(store, upload_path)
        return project_payload(document)
    except HTTPException:
        raise
    except (ProjectArchiveError, ProjectValidationError, ProjectAlreadyExists, ProjectStoreError) as exc:
        raise _translate_store_error(exc) from exc
    finally:
        upload_path.unlink(missing_ok=True)


@router.get("/{project_id}/archive", response_class=FileResponse)
def export_project_archive(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    """Build a portable archive and delete the temporary server copy after download."""
    archive_path = _temporary_archive_path(store, prefix=f".uv-export-{project_id}-")
    try:
        export_project(store, project_id, archive_path)
    except (ProjectArchiveError, ProjectValidationError, ProjectNotFound, ProjectStoreError) as exc:
        archive_path.unlink(missing_ok=True)
        raise _translate_store_error(exc) from exc

    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=f"{project_id}.uvproj.zip",
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@router.get("/{project_id}", response_model=ProjectPayload)
def get_project(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectPayload:
    try:
        return project_payload(store.load_project(project_id))
    except (ProjectValidationError, ProjectNotFound, ProjectStoreError) as exc:
        raise _translate_store_error(exc) from exc


@router.patch("/{project_id}", response_model=ProjectPayload)
def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectPayload:
    changes = request.model_fields_set
    try:
        document = store.update_project(
            project_id,
            title=request.title if "title" in changes else None,
            settings=request.settings if "settings" in changes else None,
            extensions=request.extensions if "extensions" in changes else None,
        )
        return project_payload(document)
    except (ProjectValidationError, ProjectNotFound, ProjectStoreError) as exc:
        raise _translate_store_error(exc) from exc
