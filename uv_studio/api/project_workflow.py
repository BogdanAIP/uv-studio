"""Product Orchestrator HTTP seam for project workflow state and actions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    execute_project_capability,
    get_argos_translate_adapter,
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
    get_mcp_execution_adapter,
    get_musetalk_adapter,
    get_native_videoclaw_adapter,
    get_webvtt_subtitle_adapter,
    get_whisper_cpp_adapter,
    get_whisperx_alignment_adapter,
)
from uv_studio.api.projects import get_project_store
from uv_studio.api.recipes import get_recipe_registry
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.orchestration import WORKFLOW_SCHEMA_VERSION, project_workflow_state
from uv_studio.projects.models import ProjectDocument, ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.recipes import RecipeRegistry, UnknownRecipe

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Product Orchestrator"])


class ComposePhotosActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_source_ids: list[str] = Field(min_length=1, max_length=100)
    duration_per_image_us: int = Field(default=2_000_000, ge=250_000, le=30_000_000)
    audio_source_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("image_source_ids")
    @classmethod
    def validate_image_source_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("image_source_ids entries must be non-empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("image_source_ids entries must be unique")
        return normalized

    @field_validator("audio_source_id")
    @classmethod
    def validate_audio_source_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("audio_source_id must be non-empty")
        return normalized


def _load_project(store: ProjectStore, project_id: str) -> ProjectDocument:
    try:
        return store.load_project(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def _state(
    project_id: str,
    *,
    store: ProjectStore,
    capability_registry: CapabilityRegistry,
    recipe_registry: RecipeRegistry,
) -> dict[str, Any]:
    project = _load_project(store, project_id)
    try:
        recipe = recipe_registry.get(project.recipe_id)
    except UnknownRecipe:
        recipe = None
    return project_workflow_state(project, recipe, capability_registry).to_dict()


@router.get("/{project_id}/workflow")
def get_project_workflow(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    recipe_registry: RecipeRegistry = Depends(get_recipe_registry),
) -> dict[str, Any]:
    return _state(
        project_id,
        store=store,
        capability_registry=registry,
        recipe_registry=recipe_registry,
    )


@router.post("/{project_id}/workflow/actions/{action_id}")
async def execute_project_workflow_action(
    project_id: str,
    action_id: str,
    request: ComposePhotosActionRequest,
    store: ProjectStore = Depends(get_project_store),
    registry: CapabilityRegistry = Depends(get_capability_registry),
    recipe_registry: RecipeRegistry = Depends(get_recipe_registry),
    local_ffmpeg: Any = Depends(get_local_ffmpeg_adapter),
    local_whisper_cpp: Any = Depends(get_whisper_cpp_adapter),
    local_argos_translate: Any = Depends(get_argos_translate_adapter),
    local_whisperx_alignment: Any = Depends(get_whisperx_alignment_adapter),
    local_webvtt: Any = Depends(get_webvtt_subtitle_adapter),
    local_musetalk: Any = Depends(get_musetalk_adapter),
    native_videoclaw: Any = Depends(get_native_videoclaw_adapter),
    mcp_execution: Any = Depends(get_mcp_execution_adapter),
    authorizations: OneShotAuthorizationStore = Depends(get_execution_authorization_store),
) -> dict[str, Any]:
    state = _state(
        project_id,
        store=store,
        capability_registry=registry,
        recipe_registry=recipe_registry,
    )
    if state["recipe_id"] != "photo_to_video" or action_id != "compose_photos":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow action not found for this project",
        )
    action = next(item for item in state["next_actions"] if item["action_id"] == action_id)
    if not action["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "workflow_action_blocked",
                "message": "Workflow action prerequisites are not satisfied",
                "blocked_by": action["blocked_by"],
            },
        )

    input_payload = request.model_dump(exclude_none=True)
    execution = await execute_project_capability(
        project_id=project_id,
        capability_id=action["capability_id"],
        request={"selection_policy": "local_free_first", "input": input_payload},
        store=store,
        registry=registry,
        local_ffmpeg=local_ffmpeg,
        local_whisper_cpp=local_whisper_cpp,
        local_argos_translate=local_argos_translate,
        local_whisperx_alignment=local_whisperx_alignment,
        local_webvtt=local_webvtt,
        local_musetalk=local_musetalk,
        native_videoclaw=native_videoclaw,
        mcp_execution=mcp_execution,
        authorizations=authorizations,
    )
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "action_id": action_id,
        "execution": execution,
    }
