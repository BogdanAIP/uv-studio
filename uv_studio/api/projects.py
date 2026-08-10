"""HTTP endpoints for canonical UV Studio projects."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from uv_studio.config import projects_root
from uv_studio.projects.models import ProjectDocument, ProjectValidationError
from uv_studio.projects.store import (
    ProjectAlreadyExists,
    ProjectNotFound,
    ProjectStore,
    ProjectStoreError,
)

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Projects"])


class ProjectReferencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    path: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    project_id: str
    title: str
    recipe_id: str
    created_at: str
    updated_at: str
    settings: dict[str, Any] = Field(default_factory=dict)
    sources: list[ProjectReferencePayload] = Field(default_factory=list)
    artifacts: list[ProjectReferencePayload] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    recipe_id: str = "general_video"
    settings: dict[str, Any] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)


class UpdateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=500)
    recipe_id: str | None = None
    settings: dict[str, Any] | None = None
    extensions: dict[str, Any] | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "UpdateProjectRequest":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


@lru_cache(maxsize=1)
def get_project_store() -> ProjectStore:
    return ProjectStore(projects_root())


def _payload(document: ProjectDocument) -> ProjectPayload:
    return ProjectPayload.model_validate(document.to_dict())


def _translate_store_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if isinstance(exc, ProjectAlreadyExists):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project already exists")
    if isinstance(exc, ProjectValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Project operation failed")


@router.get("", response_model=list[ProjectPayload])
def list_projects(store: ProjectStore = Depends(get_project_store)) -> list[ProjectPayload]:
    try:
        return [_payload(item) for item in store.list_projects()]
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise _translate_store_error(exc) from exc


@router.post("", response_model=ProjectPayload, status_code=status.HTTP_201_CREATED)
def create_project(
    request: CreateProjectRequest,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectPayload:
    try:
        document = store.create_project(
            title=request.title,
            recipe_id=request.recipe_id,
            settings=request.settings,
            extensions=request.extensions,
        )
        return _payload(document)
    except (ProjectValidationError, ProjectAlreadyExists, ProjectStoreError) as exc:
        raise _translate_store_error(exc) from exc


@router.get("/{project_id}", response_model=ProjectPayload)
def get_project(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> ProjectPayload:
    try:
        return _payload(store.load_project(project_id))
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
            recipe_id=request.recipe_id if "recipe_id" in changes else None,
            settings=request.settings if "settings" in changes else None,
            extensions=request.extensions if "extensions" in changes else None,
        )
        return _payload(document)
    except (ProjectValidationError, ProjectNotFound, ProjectStoreError) as exc:
        raise _translate_store_error(exc) from exc
