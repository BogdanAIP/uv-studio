"""Execution planning for UV Studio recipes.

This module answers whether a registered recipe can currently be served by an
existing compatibility target. It does not launch work and does not choose a
provider/model. Provider execution belongs to the Stage 3 Capability Registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .models import ProductionPolicy, RecipeDefinition, validate_semantic_id
from .registry import RecipeRegistry, UnknownRecipe

EXECUTION_PLAN_SCHEMA_VERSION = 1


class ExecutionCompatibility(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class InputSlotKind(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    BOOLEAN = "boolean"
    NUMBER = "number"
    CHOICE = "choice"


@dataclass(frozen=True)
class ExecutionInputSlot:
    slot_id: str
    title: str
    kind: InputSlotKind
    required: bool = True
    description: str = ""
    maps_to: str | None = None
    default: Any = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "slot_id", validate_semantic_id(self.slot_id, field_name="slot_id"))
        if not isinstance(self.kind, InputSlotKind):
            object.__setattr__(self, "kind", InputSlotKind(self.kind))
        if self.maps_to is not None:
            object.__setattr__(
                self,
                "maps_to",
                validate_semantic_id(self.maps_to, field_name="maps_to"),
            )
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("input slot title must be non-empty")
        if not isinstance(self.required, bool):
            raise ValueError("input slot required must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "title": self.title,
            "kind": self.kind.value,
            "required": self.required,
            "description": self.description,
            "maps_to": self.maps_to,
            "default": self.default,
        }


@dataclass(frozen=True)
class RuntimeConfigSlot:
    """A runtime choice needed by a compatibility target, not recipe semantics."""

    slot_id: str
    title: str
    capability_id: str
    required: bool = True
    maps_to: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "slot_id", validate_semantic_id(self.slot_id, field_name="runtime slot_id"))
        object.__setattr__(
            self,
            "capability_id",
            validate_semantic_id(self.capability_id, field_name="runtime capability_id"),
        )
        if self.maps_to is not None:
            object.__setattr__(
                self,
                "maps_to",
                validate_semantic_id(self.maps_to, field_name="runtime maps_to"),
            )
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("runtime slot title must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "title": self.title,
            "capability_id": self.capability_id,
            "required": self.required,
            "maps_to": self.maps_to,
        }


@dataclass(frozen=True)
class CompatibilityTarget:
    adapter_id: str
    target_id: str
    launch_path: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", validate_semantic_id(self.adapter_id, field_name="adapter_id"))
        object.__setattr__(self, "target_id", validate_semantic_id(self.target_id, field_name="target_id"))
        if not isinstance(self.launch_path, str) or not self.launch_path.startswith("/api/"):
            raise ValueError("launch_path must be an API path")

    def to_dict(self) -> dict[str, str]:
        return {
            "adapter_id": self.adapter_id,
            "target_id": self.target_id,
            "launch_path": self.launch_path,
        }


@dataclass(frozen=True)
class RecipeExecutionPlan:
    recipe_id: str
    recipe_title: str
    compatibility: ExecutionCompatibility
    reason: str
    input_slots: tuple[ExecutionInputSlot, ...]
    runtime_config_slots: tuple[RuntimeConfigSlot, ...]
    production_policy: ProductionPolicy
    target: CompatibilityTarget | None = None
    schema_version: int = EXECUTION_PLAN_SCHEMA_VERSION

    @property
    def can_prepare_native_execution(self) -> bool:
        return self.compatibility is ExecutionCompatibility.AVAILABLE and self.target is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recipe_id": self.recipe_id,
            "recipe_title": self.recipe_title,
            "compatibility": self.compatibility.value,
            "can_prepare_native_execution": self.can_prepare_native_execution,
            "reason": self.reason,
            "input_slots": [slot.to_dict() for slot in self.input_slots],
            "runtime_config_slots": [slot.to_dict() for slot in self.runtime_config_slots],
            "production_policy": self.production_policy.to_dict(),
            "target": None if self.target is None else self.target.to_dict(),
        }


_NATIVE = "native_videoclaw"


def _general_video(recipe: RecipeDefinition) -> RecipeExecutionPlan:
    return RecipeExecutionPlan(
        recipe_id=recipe.recipe_id,
        recipe_title=recipe.title,
        compatibility=ExecutionCompatibility.UNAVAILABLE,
        reason=(
            "A true general-video execution path is not implemented yet. The existing VideoClaw "
            "standard pipeline is narration-led and must not be used as a silent fallback."
        ),
        input_slots=(ExecutionInputSlot("brief", "Задача/идея ролика", InputSlotKind.TEXT),),
        runtime_config_slots=(),
        production_policy=recipe.production_policy,
    )


def _narrated_video(recipe: RecipeDefinition) -> RecipeExecutionPlan:
    return RecipeExecutionPlan(
        recipe_id=recipe.recipe_id,
        recipe_title=recipe.title,
        compatibility=ExecutionCompatibility.AVAILABLE,
        reason="The native VideoClaw standard pipeline is narration/topic-led and matches this recipe.",
        input_slots=(
            ExecutionInputSlot("text", "Тема или готовый дикторский текст", InputSlotKind.TEXT, maps_to="text"),
            ExecutionInputSlot("title", "Заголовок", InputSlotKind.TEXT, required=False, maps_to="title"),
        ),
        runtime_config_slots=(
            RuntimeConfigSlot("llm_model", "Текстовая модель", "text.generate", maps_to="llm_model"),
            RuntimeConfigSlot("image_model", "Модель изображений", "image.generate", maps_to="image_model"),
            RuntimeConfigSlot("video_model", "Модель видео", "video.generate", required=False, maps_to="video_model"),
        ),
        production_policy=recipe.production_policy,
        target=CompatibilityTarget(
            adapter_id=_NATIVE,
            target_id="standard",
            launch_path="/api/pipelines/standard/tasks",
        ),
    )


def _action_transfer(recipe: RecipeDefinition) -> RecipeExecutionPlan:
    return RecipeExecutionPlan(
        recipe_id=recipe.recipe_id,
        recipe_title=recipe.title,
        compatibility=ExecutionCompatibility.AVAILABLE,
        reason="The native action_transfer request contract matches source video + target image motion transfer.",
        input_slots=(
            ExecutionInputSlot("target_reference", "Целевой образ/персонаж", InputSlotKind.IMAGE, maps_to="image_path"),
            ExecutionInputSlot("source_video", "Видео с исходным движением", InputSlotKind.VIDEO, maps_to="video_path"),
            ExecutionInputSlot(
                "instruction",
                "Инструкция",
                InputSlotKind.TEXT,
                required=False,
                maps_to="prompt_text",
                default="Transfer the motion from the reference video to the subject in the target image.",
            ),
        ),
        runtime_config_slots=(
            RuntimeConfigSlot("video_model", "Модель переноса движения", "video.action_transfer", maps_to="video_model"),
        ),
        production_policy=recipe.production_policy,
        target=CompatibilityTarget(
            adapter_id=_NATIVE,
            target_id="action_transfer",
            launch_path="/api/pipelines/action_transfer/tasks",
        ),
    )


def _digital_human(recipe: RecipeDefinition) -> RecipeExecutionPlan:
    return RecipeExecutionPlan(
        recipe_id=recipe.recipe_id,
        recipe_title=recipe.title,
        compatibility=ExecutionCompatibility.PARTIAL,
        reason=(
            "The current native VideoClaw digital_human pipeline is a product-promo workflow: it accepts a character "
            "image, optional product data and model/TTS settings, but it does not accept the recipe's required supplied "
            "speech input. It must not be presented as full compatibility."
        ),
        input_slots=(
            ExecutionInputSlot("portrait", "Портрет/персонаж", InputSlotKind.IMAGE, maps_to="character_image_path"),
            ExecutionInputSlot("speech", "Готовая речь", InputSlotKind.AUDIO),
        ),
        runtime_config_slots=(),
        production_policy=recipe.production_policy,
        target=None,
    )


_RESOLVERS = {
    "general_video": _general_video,
    "narrated_video": _narrated_video,
    "action_transfer": _action_transfer,
    "digital_human": _digital_human,
}


def resolve_recipe_execution(recipe: RecipeDefinition) -> RecipeExecutionPlan:
    resolver = _RESOLVERS.get(recipe.recipe_id)
    if resolver is None:
        return RecipeExecutionPlan(
            recipe_id=recipe.recipe_id,
            recipe_title=recipe.title,
            compatibility=ExecutionCompatibility.UNAVAILABLE,
            reason="No execution compatibility target is registered for this recipe yet.",
            input_slots=tuple(
                ExecutionInputSlot(input_id, input_id.replace("_", " ").title(), InputSlotKind.TEXT)
                for input_id in recipe.required_inputs
            ),
            runtime_config_slots=(),
            production_policy=recipe.production_policy,
        )
    return resolver(recipe)


def resolve_project_execution(registry: RecipeRegistry, recipe_id: str) -> RecipeExecutionPlan:
    try:
        recipe = registry.get(recipe_id)
    except UnknownRecipe:
        return RecipeExecutionPlan(
            recipe_id=recipe_id,
            recipe_title=recipe_id,
            compatibility=ExecutionCompatibility.UNAVAILABLE,
            reason=(
                "The project references a recipe that is not installed in this UV Studio build. "
                "Project data is preserved, but execution is unavailable until that recipe is installed or migrated."
            ),
            input_slots=(),
            runtime_config_slots=(),
            production_policy=ProductionPolicy(),
        )
    return resolve_recipe_execution(recipe)
