"""Bounded download endpoint for registered project-owned artifacts."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Project Artifacts"])


def _download_name(reference, path: Path) -> str:
    original = reference.metadata.get("original_name")
    if isinstance(original, str) and original.strip():
        return Path(original.replace("\\", "/").rsplit("/", 1)[-1]).name
    return path.name


def _media_type(reference, path: Path) -> str:
    value = reference.metadata.get("content_type")
    if isinstance(value, str) and value.strip():
        return value.split(";", 1)[0].strip()
    guessed, _encoding = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


@router.get("/{project_id}/artifacts/{artifact_id}/file")
def download_project_artifact(
    project_id: str,
    artifact_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> FileResponse:
    """Download one artifact by canonical ID without exposing arbitrary host paths."""

    try:
        project = store.load_project(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    reference = next((item for item in project.artifacts if item.id == artifact_id), None)
    if reference is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    if not reference.path.startswith("artifacts/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Artifact download accepts only registered artifacts/ paths",
        )
    try:
        path = store.resolve_project_file(
            project_id,
            reference.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if not path.is_file() or path.is_symlink():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Registered artifact must be a regular project file",
        )

    return FileResponse(
        path,
        media_type=_media_type(reference, path),
        filename=_download_name(reference, path),
    )
