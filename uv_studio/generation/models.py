"""Provider-neutral named-model and generation constraint contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from uv_studio.capabilities.models import MediaKind, validate_capability_id
from uv_studio.capabilities.registry import CapabilityRegistry, UnknownCapability, UnknownOffer
from uv_studio.projects.models import ProjectValidationError, validate_identifier

GENERATION_CONTRACT_SCHEMA_VERSION = 1
MODEL_DEFINITION_SCHEMA_VERSION = 1
_MAX_CONSTRAINTS = 64
_MAX_TEXT = 4000


class GenerationValidationError(ValueError):
    pass


class ModelRegistryError(RuntimeError):
    pass


class DuplicateModel(ModelRegistryError):
    pass


class UnknownModel(ModelRegistryError):
    pass


def _bounded_text(value: Any, *, field_name: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise GenerationValidationError(f"{field_name} must be text")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise GenerationValidationError(f"{field_name} must be non-empty")
    if len(normalized) > _MAX_TEXT:
        raise GenerationValidationError(f"{field_name} exceeds {_MAX_TEXT} characters")
    return normalized


def _text_tuple(values: Iterable[str], *, field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise GenerationValidationError(f"{field_name} must be a sequence of strings")
    normalized = tuple(_bounded_text(value, field_name=field_name) for value in values)
    if len(normalized) > _MAX_CONSTRAINTS:
        raise GenerationValidationError(f"{field_name} exceeds {_MAX_CONSTRAINTS} items")
    if len(set(normalized)) != len(normalized):
        raise GenerationValidationError(f"{field_name} contains duplicates")
    return normalized


@dataclass(frozen=True)
class GenerationContract:
    """Semantic constraints that remain authoritative above provider prompts."""

    fixed_constraints: tuple[str, ...] = ()
    editable_variables: tuple[str, ...] = ()
    forbidden_changes: tuple[str, ...] = ()
    approved_reference_id: str | None = None
    schema_version: int = GENERATION_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GENERATION_CONTRACT_SCHEMA_VERSION:
            raise GenerationValidationError(
                f"GenerationContract only represents schema v{GENERATION_CONTRACT_SCHEMA_VERSION}"
            )
        object.__setattr__(
            self,
            "fixed_constraints",
            _text_tuple(self.fixed_constraints, field_name="fixed_constraints"),
        )
        object.__setattr__(
            self,
            "editable_variables",
            _text_tuple(self.editable_variables, field_name="editable_variables"),
        )
        object.__setattr__(
            self,
            "forbidden_changes",
            _text_tuple(self.forbidden_changes, field_name="forbidden_changes"),
        )
        if self.approved_reference_id is not None:
            try:
                normalized = validate_identifier(
                    self.approved_reference_id,
                    field_name="approved_reference_id",
                )
            except ProjectValidationError as exc:
                raise GenerationValidationError(str(exc)) from exc
            object.__setattr__(self, "approved_reference_id", normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fixed_constraints": list(self.fixed_constraints),
            "editable_variables": list(self.editable_variables),
            "forbidden_changes": list(self.forbidden_changes),
            "approved_reference_id": self.approved_reference_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GenerationContract":
        if not isinstance(data, Mapping):
            raise GenerationValidationError("generation contract must be a JSON object")
        allowed = {
            "schema_version",
            "fixed_constraints",
            "editable_variables",
            "forbidden_changes",
            "approved_reference_id",
        }
        unknown = set(data).difference(allowed)
        if unknown:
            raise GenerationValidationError(
                f"unsupported generation contract fields: {sorted(unknown)!r}"
            )
        try:
            schema_version = int(data.get("schema_version", GENERATION_CONTRACT_SCHEMA_VERSION))
        except (TypeError, ValueError) as exc:
            raise GenerationValidationError("generation contract schema_version must be an integer") from exc
        return cls(
            schema_version=schema_version,
            fixed_constraints=tuple(data.get("fixed_constraints", ())),
            editable_variables=tuple(data.get("editable_variables", ())),
            forbidden_changes=tuple(data.get("forbidden_changes", ())),
            approved_reference_id=data.get("approved_reference_id"),
        )


@dataclass(frozen=True)
class ModelDefinition:
    """Stable user-visible model identity mapped to a capability offer beneath it."""

    model_id: str
    title: str
    description: str
    capability_id: str
    offer_id: str
    output_kind: MediaKind
    schema_version: int = MODEL_DEFINITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MODEL_DEFINITION_SCHEMA_VERSION:
            raise GenerationValidationError(
                f"ModelDefinition only represents schema v{MODEL_DEFINITION_SCHEMA_VERSION}"
            )
        try:
            model_id = validate_capability_id(self.model_id, field_name="model_id")
            capability_id = validate_capability_id(
                self.capability_id,
                field_name="model capability_id",
            )
            offer_id = validate_capability_id(self.offer_id, field_name="model offer_id")
        except ValueError as exc:
            raise GenerationValidationError(str(exc)) from exc
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "offer_id", offer_id)
        object.__setattr__(self, "title", _bounded_text(self.title, field_name="model title"))
        object.__setattr__(
            self,
            "description",
            _bounded_text(self.description, field_name="model description"),
        )
        try:
            output_kind = self.output_kind if isinstance(self.output_kind, MediaKind) else MediaKind(self.output_kind)
        except (TypeError, ValueError) as exc:
            raise GenerationValidationError(f"invalid model output_kind: {self.output_kind!r}") from exc
        object.__setattr__(self, "output_kind", output_kind)
        if output_kind not in {MediaKind.IMAGE, MediaKind.VIDEO, MediaKind.AUDIO, MediaKind.TEXT}:
            raise GenerationValidationError(
                "named generation model output_kind must be text, image, video or audio"
            )

    def to_dict(self, capability_registry: CapabilityRegistry | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "title": self.title,
            "description": self.description,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "output_kind": self.output_kind.value,
        }
        if capability_registry is not None:
            offer = capability_registry.get_offer(self.offer_id)
            result["execution"] = {
                "adapter_id": offer.adapter_id,
                "availability": offer.availability.value,
                "reason": offer.reason,
                "locality": offer.locality.value,
                "cost_class": offer.cost_class.value,
                "asynchronous": offer.asynchronous,
            }
        return result


class ModelRegistry:
    """Backend authority for named model identity, separate from provider transport."""

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        models: Iterable[ModelDefinition] = (),
    ) -> None:
        self.capability_registry = capability_registry
        self._models: dict[str, ModelDefinition] = {}
        for model in models:
            self.register(model)

    def register(self, model: ModelDefinition) -> ModelDefinition:
        if not isinstance(model, ModelDefinition):
            raise GenerationValidationError("model registry accepts only ModelDefinition values")
        if model.model_id in self._models:
            raise DuplicateModel(model.model_id)
        try:
            capability = self.capability_registry.get_capability(model.capability_id)
            offer = self.capability_registry.get_offer(model.offer_id)
        except (UnknownCapability, UnknownOffer) as exc:
            raise ModelRegistryError(
                f"model {model.model_id!r} references unknown capability/offer"
            ) from exc
        if offer.capability_id != capability.capability_id:
            raise ModelRegistryError(
                f"model {model.model_id!r} offer does not implement capability {model.capability_id!r}"
            )
        if model.output_kind not in capability.output_kinds:
            raise ModelRegistryError(
                f"model {model.model_id!r} output kind {model.output_kind.value!r} "
                f"is not declared by capability {model.capability_id!r}"
            )
        self._models[model.model_id] = model
        return model

    def get(self, model_id: str) -> ModelDefinition:
        try:
            normalized = validate_capability_id(model_id, field_name="model_id")
        except ValueError as exc:
            raise UnknownModel(model_id) from exc
        try:
            return self._models[normalized]
        except KeyError as exc:
            raise UnknownModel(normalized) from exc

    def list(self) -> tuple[ModelDefinition, ...]:
        return tuple(sorted(self._models.values(), key=lambda item: item.model_id))

    def describe(self, model_id: str) -> dict[str, Any]:
        return self.get(model_id).to_dict(self.capability_registry)

    def catalog(self) -> tuple[dict[str, Any], ...]:
        return tuple(model.to_dict(self.capability_registry) for model in self.list())
