"""Provider-separated semantic capability contracts for UV Studio."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

CAPABILITY_SCHEMA_VERSION = 1
_SEMANTIC_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


class CapabilityValidationError(ValueError):
    pass


def validate_capability_id(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SEMANTIC_ID_RE.fullmatch(value):
        raise CapabilityValidationError(
            f"{field_name} must match {_SEMANTIC_ID_RE.pattern!r}; got {value!r}"
        )
    return value


def _clean_text(value: str, *, field_name: str, max_length: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityValidationError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > max_length:
        raise CapabilityValidationError(f"{field_name} is too long")
    return normalized


def _enum_value(value: Any, enum_type: type[Enum], *, field_name: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise CapabilityValidationError(f"invalid {field_name}: {value!r}") from exc


class OperationKind(str, Enum):
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    UNDERSTANDING = "understanding"
    SPEECH = "speech"
    DETERMINISTIC_MEDIA = "deterministic_media"
    ASSEMBLY = "assembly"


class MediaKind(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    TIMELINE = "timeline"
    METADATA = "metadata"


class LocalityClass(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


class CostClass(str, Enum):
    FREE = "free"
    POTENTIALLY_PAID = "potentially_paid"
    PAID = "paid"


class AdapterKind(str, Enum):
    LOCAL = "local"
    NATIVE = "native"
    MCP = "mcp"
    RUNTIME = "runtime"


class OfferAvailability(str, Enum):
    AVAILABLE = "available"
    CONFIGURATION_REQUIRED = "configuration_required"
    UNAVAILABLE = "unavailable"


def _media_tuple(values: tuple[MediaKind | str, ...], *, field_name: str) -> tuple[MediaKind, ...]:
    if not isinstance(values, tuple):
        raise CapabilityValidationError(f"{field_name} must be a tuple")
    normalized = tuple(_enum_value(value, MediaKind, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CapabilityValidationError(f"{field_name} contains duplicates")
    return normalized


def _feature_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise CapabilityValidationError("features must be a tuple")
    normalized = tuple(validate_capability_id(value, field_name="feature") for value in values)
    if len(set(normalized)) != len(normalized):
        raise CapabilityValidationError("features contains duplicates")
    return normalized


@dataclass(frozen=True)
class CapabilityEffects:
    """Stable semantic effects for policy/trace consumers above provider offers.

    Cost and locality remain offer-specific permission facts. ``cost_bearing``
    means this semantic operation may incur external cost for at least one
    execution mapping; D-017 still evaluates the selected offer before launch.
    """

    mutates_project: bool = False
    mutates_timeline: bool = False
    generates_media: bool = False
    destructive: bool = False
    long_running: bool = False
    reversible: bool = False
    cost_bearing: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "mutates_project",
            "mutates_timeline",
            "generates_media",
            "destructive",
            "long_running",
            "reversible",
            "cost_bearing",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise CapabilityValidationError(f"effect {field_name} must be boolean")

    def to_dict(self) -> dict[str, bool]:
        return {
            "mutates_project": self.mutates_project,
            "mutates_timeline": self.mutates_timeline,
            "generates_media": self.generates_media,
            "destructive": self.destructive,
            "long_running": self.long_running,
            "reversible": self.reversible,
            "cost_bearing": self.cost_bearing,
        }


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    title: str
    description: str
    operation_kind: OperationKind
    input_kinds: tuple[MediaKind, ...]
    output_kinds: tuple[MediaKind, ...]
    asynchronous: bool = False
    schema_version: int = CAPABILITY_SCHEMA_VERSION
    effects: CapabilityEffects = field(default_factory=CapabilityEffects)

    def __post_init__(self) -> None:
        if self.schema_version != CAPABILITY_SCHEMA_VERSION:
            raise CapabilityValidationError(
                f"CapabilityDefinition only represents schema v{CAPABILITY_SCHEMA_VERSION}"
            )
        object.__setattr__(
            self,
            "capability_id",
            validate_capability_id(self.capability_id, field_name="capability_id"),
        )
        object.__setattr__(self, "title", _clean_text(self.title, field_name="title", max_length=200))
        object.__setattr__(self, "description", _clean_text(self.description, field_name="description"))
        object.__setattr__(
            self,
            "operation_kind",
            _enum_value(self.operation_kind, OperationKind, field_name="operation_kind"),
        )
        object.__setattr__(self, "input_kinds", _media_tuple(self.input_kinds, field_name="input_kinds"))
        object.__setattr__(self, "output_kinds", _media_tuple(self.output_kinds, field_name="output_kinds"))
        if not self.input_kinds or not self.output_kinds:
            raise CapabilityValidationError("capability input/output kinds must be non-empty")
        if not isinstance(self.asynchronous, bool):
            raise CapabilityValidationError("asynchronous must be boolean")
        if not isinstance(self.effects, CapabilityEffects):
            raise CapabilityValidationError("effects must be CapabilityEffects")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "title": self.title,
            "description": self.description,
            "operation_kind": self.operation_kind.value,
            "input_kinds": [item.value for item in self.input_kinds],
            "output_kinds": [item.value for item in self.output_kinds],
            "asynchronous": self.asynchronous,
            "effects": self.effects.to_dict(),
        }


@dataclass(frozen=True)
class AdapterDefinition:
    adapter_id: str
    title: str
    description: str
    kind: AdapterKind

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", validate_capability_id(self.adapter_id, field_name="adapter_id"))
        object.__setattr__(self, "title", _clean_text(self.title, field_name="adapter title", max_length=200))
        object.__setattr__(self, "description", _clean_text(self.description, field_name="adapter description"))
        object.__setattr__(self, "kind", _enum_value(self.kind, AdapterKind, field_name="adapter kind"))

    def to_dict(self) -> dict[str, str]:
        return {
            "adapter_id": self.adapter_id,
            "title": self.title,
            "description": self.description,
            "kind": self.kind.value,
        }


@dataclass(frozen=True)
class CapabilityOffer:
    offer_id: str
    capability_id: str
    adapter_id: str
    title: str
    availability: OfferAvailability
    reason: str
    locality: LocalityClass
    cost_class: CostClass
    asynchronous: bool
    features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "offer_id", validate_capability_id(self.offer_id, field_name="offer_id"))
        object.__setattr__(
            self,
            "capability_id",
            validate_capability_id(self.capability_id, field_name="offer capability_id"),
        )
        object.__setattr__(self, "adapter_id", validate_capability_id(self.adapter_id, field_name="offer adapter_id"))
        object.__setattr__(self, "title", _clean_text(self.title, field_name="offer title", max_length=200))
        object.__setattr__(self, "reason", _clean_text(self.reason, field_name="offer reason"))
        object.__setattr__(
            self,
            "availability",
            _enum_value(self.availability, OfferAvailability, field_name="availability"),
        )
        object.__setattr__(self, "locality", _enum_value(self.locality, LocalityClass, field_name="locality"))
        object.__setattr__(self, "cost_class", _enum_value(self.cost_class, CostClass, field_name="cost_class"))
        if not isinstance(self.asynchronous, bool):
            raise CapabilityValidationError("offer asynchronous must be boolean")
        object.__setattr__(self, "features", _feature_tuple(self.features))

    def to_dict(self) -> dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "capability_id": self.capability_id,
            "adapter_id": self.adapter_id,
            "title": self.title,
            "availability": self.availability.value,
            "reason": self.reason,
            "locality": self.locality.value,
            "cost_class": self.cost_class.value,
            "asynchronous": self.asynchronous,
            "features": list(self.features),
        }
