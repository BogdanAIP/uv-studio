"""Project-level execution planning endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.api.recipes import get_recipe_registry
from uv_studio.capabilities import CapabilityRegistry, UnknownCapability
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.recipes import resolve_project_execution

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Execution Plans"])

_STAGE8_CAPABILITY_RECIPES = {
    "photo_to_video": (
        "video.compose_photos",
        "Photo-to-video is ready through the registered video.compose_photos semantic capability.",
        "Photo-to-video is configured as a UV-owned semantic workflow, but its video.compose_photos local media capability is not executable on this machine yet.",
    ),
    "visualizer": (
        "audio.visualize",
        "Visualizer is ready through the registered audio.visualize semantic capability.",
        "Visualizer is configured as a UV-owned semantic workflow, but its audio.visualize local media capability is not executable on this machine yet.",
    ),
    "performance_lip_sync": (
        "video.digital_human",
        "Performance/lip-sync is ready through a verified supplied portrait + speech video.digital_human offer.",
        "Performance/lip-sync is capability-gated because video.digital_human has no verified executable supplied portrait + speech offer. Configure and verify the optional local MuseTalk pack before execution; no incompatible legacy fallback is used.",
    ),
}


def _capability_summary(registry: CapabilityRegistry, capability_id: str) -> dict[str, Any]:
    try:
        capability = registry.get_capability(capability_id)
    except UnknownCapability:
        return {
            "known": False,
            "offer_summary": {
                "total": 0,
                "available": 0,
                "configuration_required": 0,
                "unavailable": 0,
            },
        }
    return {
        "known": True,
        "operation_kind": capability.operation_kind.value,
        "offer_summary": registry.offer_summary(capability_id),
    }


def _project_stage8_capability_status(
    payload: dict[str, Any],
    registry: CapabilityRegistry,
) -> None:
    projection = _STAGE8_CAPABILITY_RECIPES.get(payload.get("recipe_id"))
    if projection is None:
        return
    capability_id, ready_reason, blocked_reason = projection
    capability_status = _capability_summary(registry, capability_id)
    available = capability_status["offer_summary"]["available"] > 0
    payload["compatibility"] = "available" if available else "partial"
    payload["reason"] = ready_reason if available else blocked_reason
    payload["can_prepare_native_execution"] = False
    payload["target"] = None
    payload["runtime_config_slots"] = [
        {
            "slot_id": "stage8_execution_capability",
            "title": "Исполняемая возможность режима",
            "capability_id": capability_id,
            "required": True,
            "maps_to": None,
            "capability_status": capability_status,
        }
    ]


@router.get("/{project_id}/execution-plan")
def get_project_execution_plan(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
    capability_registry: CapabilityRegistry = Depends(get_capability_registry),
) -> dict[str, Any]:
    try:
        project = store.load_project(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except ProjectValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProjectStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    plan = resolve_project_execution(get_recipe_registry(), project.recipe_id)
    payload = plan.to_dict()
    payload["project_id"] = project.project_id
    payload["runtime_config_slots"] = [
        {
            **slot,
            "capability_status": _capability_summary(capability_registry, slot["capability_id"]),
        }
        for slot in payload["runtime_config_slots"]
    ]
    _project_stage8_capability_status(payload, capability_registry)
    return payload
