"""Project-level execution planning endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.api.recipes import get_recipe_registry
from uv_studio.capabilities import UnknownCapability
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.recipes import resolve_project_execution

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Execution Plans"])


def _capability_summary(capability_id: str) -> dict[str, Any]:
    registry = get_capability_registry()
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


@router.get("/{project_id}/execution-plan")
def get_project_execution_plan(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
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
            "capability_status": _capability_summary(slot["capability_id"]),
        }
        for slot in payload["runtime_config_slots"]
    ]
    return payload
