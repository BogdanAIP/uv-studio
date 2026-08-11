"""Provider-neutral recipe contracts for UV Studio.

Recipe definitions describe *what* a project workflow needs and how carefully it
should be produced. They deliberately do not name API vendors or execution
runtimes; Stage 3 will resolve semantic capabilities to concrete adapters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

RECIPE_SCHEMA_VERSION = 1
_SEMANTIC_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


class RecipeValidationError(ValueError):
    pass


def validate_semantic_id(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SEMANTIC_ID_RE.fullmatch(value):
        raise RecipeValidationError(
            f"{field_name} must match {_SEMANTIC_ID_RE.pattern!r}; got {value!r}"
        )
    return value


def _clean_text(value: str, *, field_name: str, max_length: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecipeValidationError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > max_length:
        raise RecipeValidationError(f"{field_name} is too long ({len(normalized)} > {max_length})")
    return normalized


def _semantic_tuple(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise RecipeValidationError(f"{field_name} must be a tuple")
    normalized = tuple(validate_semantic_id(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise RecipeValidationError(f"{field_name} contains duplicate values")
    return normalized


class PolicyMode(str, Enum):
    OFF = "off"
    OPTIONAL = "optional"
    REQUIRED = "required"


def _policy_mode(value: PolicyMode | str, *, field_name: str) -> PolicyMode:
    if isinstance(value, PolicyMode):
        return value
    try:
        return PolicyMode(value)
    except (TypeError, ValueError) as exc:
        raise RecipeValidationError(
            f"{field_name} must be one of: {', '.join(item.value for item in PolicyMode)}"
        ) from exc


@dataclass(frozen=True)
class ProductionPolicy:
    """Provider-independent production discipline selected by a recipe."""

    source_review: PolicyMode = PolicyMode.OFF
    direction_gate: PolicyMode = PolicyMode.OFF
    sample_first: PolicyMode = PolicyMode.OFF
    plan_gate: PolicyMode = PolicyMode.OFF
    scene_ledger: PolicyMode = PolicyMode.OFF
    final_review: PolicyMode = PolicyMode.OFF
    continuity: PolicyMode = PolicyMode.OFF

    def __post_init__(self) -> None:
        for field_name in (
            "source_review",
            "direction_gate",
            "sample_first",
            "plan_gate",
            "scene_ledger",
            "final_review",
            "continuity",
        ):
            object.__setattr__(
                self,
                field_name,
                _policy_mode(getattr(self, field_name), field_name=field_name),
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "source_review": self.source_review.value,
            "direction_gate": self.direction_gate.value,
            "sample_first": self.sample_first.value,
            "plan_gate": self.plan_gate.value,
            "scene_ledger": self.scene_ledger.value,
            "final_review": self.final_review.value,
            "continuity": self.continuity.value,
        }


@dataclass(frozen=True)
class RecipeStep:
    """One logical workflow step; execution is intentionally not implemented here."""

    step_id: str
    title: str
    description: str
    capability_id: str | None = None
    optional: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", validate_semantic_id(self.step_id, field_name="step_id"))
        object.__setattr__(self, "title", _clean_text(self.title, field_name="step title", max_length=200))
        object.__setattr__(
            self,
            "description",
            _clean_text(self.description, field_name="step description", max_length=1000),
        )
        if self.capability_id is not None:
            object.__setattr__(
                self,
                "capability_id",
                validate_semantic_id(self.capability_id, field_name="capability_id"),
            )
        if not isinstance(self.optional, bool):
            raise RecipeValidationError("step optional must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "capability_id": self.capability_id,
            "optional": self.optional,
        }


@dataclass(frozen=True)
class RecipeUIHints:
    """Small progressive-disclosure hints, not a second UI schema language."""

    category: str
    primary_input_label: str
    visible_sections: tuple[str, ...] = ()
    advanced_sections: tuple[str, ...] = ()
    featured: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", validate_semantic_id(self.category, field_name="UI category"))
        object.__setattr__(
            self,
            "primary_input_label",
            _clean_text(self.primary_input_label, field_name="primary input label", max_length=120),
        )
        object.__setattr__(
            self,
            "visible_sections",
            _semantic_tuple(self.visible_sections, field_name="visible_sections"),
        )
        object.__setattr__(
            self,
            "advanced_sections",
            _semantic_tuple(self.advanced_sections, field_name="advanced_sections"),
        )
        overlap = set(self.visible_sections) & set(self.advanced_sections)
        if overlap:
            raise RecipeValidationError(f"UI sections cannot be both visible and advanced: {sorted(overlap)!r}")
        if not isinstance(self.featured, bool):
            raise RecipeValidationError("featured must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "primary_input_label": self.primary_input_label,
            "visible_sections": list(self.visible_sections),
            "advanced_sections": list(self.advanced_sections),
            "featured": self.featured,
        }


@dataclass(frozen=True)
class RecipeDefinition:
    recipe_id: str
    title: str
    description: str
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    optional_capabilities: tuple[str, ...]
    steps: tuple[RecipeStep, ...]
    production_policy: ProductionPolicy = field(default_factory=ProductionPolicy)
    ui: RecipeUIHints = field(
        default_factory=lambda: RecipeUIHints(category="general", primary_input_label="Задача")
    )
    schema_version: int = RECIPE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RECIPE_SCHEMA_VERSION:
            raise RecipeValidationError(
                f"RecipeDefinition only represents schema v{RECIPE_SCHEMA_VERSION}; got v{self.schema_version}"
            )
        object.__setattr__(
            self,
            "recipe_id",
            validate_semantic_id(self.recipe_id, field_name="recipe_id"),
        )
        object.__setattr__(self, "title", _clean_text(self.title, field_name="recipe title", max_length=200))
        object.__setattr__(
            self,
            "description",
            _clean_text(self.description, field_name="recipe description", max_length=2000),
        )
        object.__setattr__(
            self,
            "required_inputs",
            _semantic_tuple(self.required_inputs, field_name="required_inputs"),
        )
        object.__setattr__(
            self,
            "optional_inputs",
            _semantic_tuple(self.optional_inputs, field_name="optional_inputs"),
        )
        object.__setattr__(
            self,
            "required_capabilities",
            _semantic_tuple(self.required_capabilities, field_name="required_capabilities"),
        )
        object.__setattr__(
            self,
            "optional_capabilities",
            _semantic_tuple(self.optional_capabilities, field_name="optional_capabilities"),
        )
        if set(self.required_inputs) & set(self.optional_inputs):
            raise RecipeValidationError("an input cannot be both required and optional")
        if set(self.required_capabilities) & set(self.optional_capabilities):
            raise RecipeValidationError("a capability cannot be both required and optional")
        if not isinstance(self.steps, tuple) or not self.steps:
            raise RecipeValidationError("steps must be a non-empty tuple")
        if not all(isinstance(step, RecipeStep) for step in self.steps):
            raise RecipeValidationError("steps must contain RecipeStep values")
        step_ids = [step.step_id for step in self.steps]
        if len(set(step_ids)) != len(step_ids):
            raise RecipeValidationError("step_id values must be unique within a recipe")
        declared_capabilities = set(self.required_capabilities) | set(self.optional_capabilities)
        undeclared = sorted(
            {
                step.capability_id
                for step in self.steps
                if step.capability_id is not None and step.capability_id not in declared_capabilities
            }
        )
        if undeclared:
            raise RecipeValidationError(
                f"steps reference undeclared capabilities: {undeclared!r}"
            )
        if not isinstance(self.production_policy, ProductionPolicy):
            raise RecipeValidationError("production_policy must be ProductionPolicy")
        if not isinstance(self.ui, RecipeUIHints):
            raise RecipeValidationError("ui must be RecipeUIHints")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recipe_id": self.recipe_id,
            "title": self.title,
            "description": self.description,
            "required_inputs": list(self.required_inputs),
            "optional_inputs": list(self.optional_inputs),
            "required_capabilities": list(self.required_capabilities),
            "optional_capabilities": list(self.optional_capabilities),
            "steps": [step.to_dict() for step in self.steps],
            "production_policy": self.production_policy.to_dict(),
            "ui": self.ui.to_dict(),
        }
