"""Intent-first creative project HTTP adapter."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.api.recipes import get_recipe_registry
from uv_studio.application.creative_projects import CreativeProjectError, CreativeProjectService
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.projects.store import ProjectStore
from uv_studio.recipes import RecipeRegistry

router = APIRouter(prefix="/api/uv", tags=["UV Studio Creative Projects"])


class CreateCreativeProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=20_000)
    title: str | None = Field(default=None, min_length=1, max_length=500)


class UpdateCreativeIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str | None = Field(default=None, min_length=1, max_length=20_000)
    script: str | None = Field(default=None, max_length=100_000)

    @model_validator(mode="after")
    def require_change(self) -> "UpdateCreativeIntentRequest":
        if not self.model_fields_set:
            raise ValueError("at least one creative intent field is required")
        return self


def _service(
    store: ProjectStore,
    registry: CapabilityRegistry,
    recipe_registry: RecipeRegistry,
) -> CreativeProjectService:
    return CreativeProjectService(store, registry, recipe_registry)


def _translate(exc: CreativeProjectError) -> HTTPException:
    message = str(exc)
    if message == "project not found":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if "not an intent-first creative project" in message:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


@router.post("/creative-projects", status_code=status.HTTP_201_CREATED)
def create_creative_project(
    request: CreateCreativeProjectRequest,
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    recipe_registry: RecipeRegistry = Depends(get_recipe_registry),
) -> dict[str, Any]:
    try:
        project = _service(store, registry, recipe_registry).create(
            goal=request.goal,
            title=request.title,
        )
        return project.to_dict()
    except CreativeProjectError as exc:
        raise _translate(exc) from exc


@router.get("/projects/{project_id}/creative-plan")
def get_creative_plan(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    recipe_registry: RecipeRegistry = Depends(get_recipe_registry),
) -> dict[str, Any]:
    try:
        return _service(store, registry, recipe_registry).plan(project_id)
    except CreativeProjectError as exc:
        raise _translate(exc) from exc


@router.patch("/projects/{project_id}/creative-intent")
def update_creative_intent(
    project_id: str,
    request: UpdateCreativeIntentRequest,
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    recipe_registry: RecipeRegistry = Depends(get_recipe_registry),
) -> dict[str, Any]:
    try:
        project = _service(store, registry, recipe_registry).update_intent(
            project_id,
            goal=request.goal if "goal" in request.model_fields_set else None,
            script=request.script if "script" in request.model_fields_set else None,
        )
        return project.to_dict()
    except CreativeProjectError as exc:
        raise _translate(exc) from exc
