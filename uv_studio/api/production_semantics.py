"""HTTP boundary for shared production semantics and micro-drama extensions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, Literal, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from uv_studio.api.project_common import get_project_store
from uv_studio.production.commands import ProductionCommandResult, ProductionSemanticService
from uv_studio.production.micro_drama import (
    Character,
    Location,
    MicroDramaDocument,
    SceneContinuity,
    Story,
)
from uv_studio.production.semantics import ProductionSemanticError
from uv_studio.projects.identity import StudioIdentityError
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.production_state import ProductionStateError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError
from uv_studio.projects.timeline import TimelineError
from uv_studio.projects.transactions import ProjectTransactionError

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Production"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateScenePayload(_StrictModel):
    command: Literal["create_scene"]
    scene_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(default="", max_length=4000)


class CreateShotPayload(_StrictModel):
    command: Literal["create_shot"]
    shot_id: str = Field(min_length=1, max_length=128)
    scene_id: str = Field(min_length=1, max_length=128)
    intent: str = Field(min_length=1, max_length=4000)
    reference_ids: list[str] = Field(default_factory=list)


class RegisterTakePayload(_StrictModel):
    command: Literal["register_take"]
    take_id: str = Field(min_length=1, max_length=128)
    shot_id: str = Field(min_length=1, max_length=128)
    reference_id: str = Field(min_length=1, max_length=128)
    label: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=4000)


class StoryInput(_StrictModel):
    title: str = Field(min_length=1, max_length=500)
    premise: str = Field(default="", max_length=8000)
    synopsis: str = Field(default="", max_length=8000)


class CharacterInput(_StrictModel):
    character_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=8000)


class LocationInput(_StrictModel):
    location_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=8000)


class SceneContinuityInput(_StrictModel):
    scene_id: str = Field(min_length=1, max_length=128)
    character_ids: list[str] = Field(default_factory=list)
    location_id: str | None = Field(default=None, min_length=1, max_length=128)
    canon_facts: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=8000)


class MicroDramaInput(_StrictModel):
    story: StoryInput | None = None
    characters: list[CharacterInput] = Field(default_factory=list)
    locations: list[LocationInput] = Field(default_factory=list)
    scene_continuity: list[SceneContinuityInput] = Field(default_factory=list)


class SetMicroDramaContextPayload(_StrictModel):
    command: Literal["set_micro_drama_context"]
    document: MicroDramaInput


class AcceptTakePayload(_StrictModel):
    command: Literal["accept_take"]
    take_id: str = Field(min_length=1, max_length=128)
    timeline_start_us: int = Field(ge=0)
    source_start_us: int = Field(default=0, ge=0)
    duration_us: int = Field(gt=0)
    track_id: str = Field(default="production_video", min_length=1, max_length=128)
    clip_id: str | None = Field(default=None, min_length=1, max_length=128)


ProductionCommandPayload = Annotated[
    Union[
        CreateScenePayload,
        CreateShotPayload,
        RegisterTakePayload,
        SetMicroDramaContextPayload,
        AcceptTakePayload,
    ],
    Field(discriminator="command"),
]


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=404, detail="Project not found")
    if isinstance(
        exc,
        (
            ProductionSemanticError,
            StudioIdentityError,
            ProductionStateError,
            ProjectTransactionError,
            TimelineError,
            ProjectValidationError,
        ),
    ):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ProjectStoreError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail="Production operation failed")


def _micro_drama_document(payload: MicroDramaInput) -> MicroDramaDocument:
    return MicroDramaDocument(
        story=(
            None
            if payload.story is None
            else Story(
                title=payload.story.title,
                premise=payload.story.premise,
                synopsis=payload.story.synopsis,
            )
        ),
        characters=tuple(
            Character(
                character_id=item.character_id,
                name=item.name,
                description=item.description,
            )
            for item in payload.characters
        ),
        locations=tuple(
            Location(
                location_id=item.location_id,
                name=item.name,
                description=item.description,
            )
            for item in payload.locations
        ),
        scene_continuity=tuple(
            SceneContinuity(
                scene_id=item.scene_id,
                character_ids=tuple(item.character_ids),
                location_id=item.location_id,
                canon_facts=tuple(item.canon_facts),
                notes=item.notes,
            )
            for item in payload.scene_continuity
        ),
    )


def _handle_create_scene(
    service: ProductionSemanticService,
    project_id: str,
    payload: CreateScenePayload,
) -> ProductionCommandResult:
    return service.create_scene(
        project_id,
        scene_id=payload.scene_id,
        title=payload.title,
        summary=payload.summary,
    )


def _handle_create_shot(
    service: ProductionSemanticService,
    project_id: str,
    payload: CreateShotPayload,
) -> ProductionCommandResult:
    return service.create_shot(
        project_id,
        shot_id=payload.shot_id,
        scene_id=payload.scene_id,
        intent=payload.intent,
        reference_ids=tuple(payload.reference_ids),
    )


def _handle_register_take(
    service: ProductionSemanticService,
    project_id: str,
    payload: RegisterTakePayload,
) -> ProductionCommandResult:
    return service.register_take(
        project_id,
        take_id=payload.take_id,
        shot_id=payload.shot_id,
        reference_id=payload.reference_id,
        label=payload.label,
        notes=payload.notes,
    )


def _handle_set_micro_drama_context(
    service: ProductionSemanticService,
    project_id: str,
    payload: SetMicroDramaContextPayload,
) -> ProductionCommandResult:
    return service.set_micro_drama_context(
        project_id,
        _micro_drama_document(payload.document),
    )


def _handle_accept_take(
    service: ProductionSemanticService,
    project_id: str,
    payload: AcceptTakePayload,
) -> ProductionCommandResult:
    return service.accept_take(
        project_id,
        take_id=payload.take_id,
        timeline_start_us=payload.timeline_start_us,
        source_start_us=payload.source_start_us,
        duration_us=payload.duration_us,
        track_id=payload.track_id,
        clip_id=payload.clip_id,
    )


ProductionCommandHandler = Callable[
    [ProductionSemanticService, str, Any],
    ProductionCommandResult,
]

_COMMAND_HANDLERS: dict[type[_StrictModel], ProductionCommandHandler] = {
    CreateScenePayload: _handle_create_scene,
    CreateShotPayload: _handle_create_shot,
    RegisterTakePayload: _handle_register_take,
    SetMicroDramaContextPayload: _handle_set_micro_drama_context,
    AcceptTakePayload: _handle_accept_take,
}


@router.get("/{project_id}/studio/production", response_model=dict[str, Any])
def get_production_semantics(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        return ProductionSemanticService(store).state(project_id).to_dict()
    except Exception as exc:
        raise _translate(exc) from exc


@router.get(
    "/{project_id}/studio/production/micro-drama",
    response_model=dict[str, Any],
)
def get_micro_drama_context(
    project_id: str,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    try:
        return ProductionSemanticService(store).micro_drama_state(project_id).to_dict()
    except Exception as exc:
        raise _translate(exc) from exc


@router.post(
    "/{project_id}/studio/production/commands",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
def execute_production_command(
    project_id: str,
    payload: ProductionCommandPayload,
    store: ProjectStore = Depends(get_project_store),
) -> dict[str, Any]:
    service = ProductionSemanticService(store)
    try:
        handler = _COMMAND_HANDLERS.get(type(payload))
        if handler is None:  # pragma: no cover - discriminated union rejects this first.
            raise ProductionSemanticError("unsupported production command")
        return handler(service, project_id, payload).to_dict()
    except Exception as exc:
        raise _translate(exc) from exc
