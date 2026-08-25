"""Micro-drama extensions over the shared Scene/Shot/Take production core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from uv_studio.production.semantics import ProductionSemanticError
from uv_studio.projects.models import ProjectValidationError, validate_identifier

MICRO_DRAMA_SCHEMA_VERSION = 1
MICRO_DRAMA_DOCUMENT_ID = "micro_drama"
MICRO_DRAMA_PATH = "production/micro_drama.json"

_MAX_TEXT_LENGTH = 8000


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise ProductionSemanticError(str(exc)) from exc


def _text(
    value: Any,
    *,
    field_name: str,
    required: bool = False,
    limit: int = _MAX_TEXT_LENGTH,
) -> str:
    if not isinstance(value, str):
        raise ProductionSemanticError(f"{field_name} must be text")
    normalized = value.strip()
    if required and not normalized:
        raise ProductionSemanticError(f"{field_name} must be non-empty text")
    if len(normalized) > limit:
        raise ProductionSemanticError(f"{field_name} must be <= {limit} characters")
    return normalized


def _id_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ProductionSemanticError(f"{field_name} must be a list")
    normalized = tuple(_identifier(item, field_name=f"{field_name} item") for item in value)
    if len(normalized) != len(set(normalized)):
        raise ProductionSemanticError(f"{field_name} values must be unique")
    return normalized


def _text_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ProductionSemanticError(f"{field_name} must be a list")
    normalized = tuple(
        _text(item, field_name=f"{field_name} item", required=True, limit=2000)
        for item in value
    )
    if len(normalized) != len(set(normalized)):
        raise ProductionSemanticError(f"{field_name} values must be unique")
    return normalized


@dataclass(frozen=True)
class Story:
    title: str
    premise: str = ""
    synopsis: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "title",
            _text(self.title, field_name="story title", required=True, limit=500),
        )
        object.__setattr__(self, "premise", _text(self.premise, field_name="story premise"))
        object.__setattr__(self, "synopsis", _text(self.synopsis, field_name="story synopsis"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "premise": self.premise,
            "synopsis": self.synopsis,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Story":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("story must be a JSON object")
        allowed = {"title", "premise", "synopsis"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(f"unsupported story fields: {sorted(unknown)!r}")
        if "title" not in data:
            raise ProductionSemanticError("story is missing title")
        return cls(
            title=data["title"],
            premise=data.get("premise", ""),
            synopsis=data.get("synopsis", ""),
        )


@dataclass(frozen=True)
class Character:
    character_id: str
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "character_id",
            _identifier(self.character_id, field_name="character_id"),
        )
        object.__setattr__(
            self,
            "name",
            _text(self.name, field_name="character name", required=True, limit=500),
        )
        object.__setattr__(
            self,
            "description",
            _text(self.description, field_name="character description"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Character":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("character must be a JSON object")
        allowed = {"character_id", "name", "description"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(
                f"unsupported character fields: {sorted(unknown)!r}"
            )
        missing = {"character_id", "name"}.difference(data)
        if missing:
            raise ProductionSemanticError(
                f"character is missing fields: {sorted(missing)!r}"
            )
        return cls(
            character_id=data["character_id"],
            name=data["name"],
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class Location:
    location_id: str
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "location_id",
            _identifier(self.location_id, field_name="location_id"),
        )
        object.__setattr__(
            self,
            "name",
            _text(self.name, field_name="location name", required=True, limit=500),
        )
        object.__setattr__(
            self,
            "description",
            _text(self.description, field_name="location description"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Location":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("location must be a JSON object")
        allowed = {"location_id", "name", "description"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(
                f"unsupported location fields: {sorted(unknown)!r}"
            )
        missing = {"location_id", "name"}.difference(data)
        if missing:
            raise ProductionSemanticError(
                f"location is missing fields: {sorted(missing)!r}"
            )
        return cls(
            location_id=data["location_id"],
            name=data["name"],
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class SceneContinuity:
    scene_id: str
    character_ids: tuple[str, ...] = ()
    location_id: str | None = None
    canon_facts: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scene_id",
            _identifier(self.scene_id, field_name="continuity scene_id"),
        )
        object.__setattr__(
            self,
            "character_ids",
            _id_tuple(self.character_ids, field_name="continuity character_ids"),
        )
        location = self.location_id
        if location is not None:
            location = _identifier(location, field_name="continuity location_id")
        object.__setattr__(self, "location_id", location)
        object.__setattr__(
            self,
            "canon_facts",
            _text_tuple(self.canon_facts, field_name="continuity canon_facts"),
        )
        object.__setattr__(self, "notes", _text(self.notes, field_name="continuity notes"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "character_ids": list(self.character_ids),
            "location_id": self.location_id,
            "canon_facts": list(self.canon_facts),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SceneContinuity":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("scene continuity must be a JSON object")
        allowed = {
            "scene_id",
            "character_ids",
            "location_id",
            "canon_facts",
            "notes",
        }
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(
                f"unsupported scene continuity fields: {sorted(unknown)!r}"
            )
        if "scene_id" not in data:
            raise ProductionSemanticError("scene continuity is missing scene_id")
        return cls(
            scene_id=data["scene_id"],
            character_ids=tuple(data.get("character_ids", [])),
            location_id=data.get("location_id"),
            canon_facts=tuple(data.get("canon_facts", [])),
            notes=data.get("notes", ""),
        )


@dataclass(frozen=True)
class MicroDramaDocument:
    story: Story | None = None
    characters: tuple[Character, ...] = ()
    locations: tuple[Location, ...] = ()
    scene_continuity: tuple[SceneContinuity, ...] = ()
    schema_version: int = MICRO_DRAMA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MICRO_DRAMA_SCHEMA_VERSION:
            raise ProductionSemanticError(
                f"unsupported micro-drama schema: {self.schema_version!r}; "
                f"supported={MICRO_DRAMA_SCHEMA_VERSION}"
            )
        if self.story is not None and not isinstance(self.story, Story):
            raise ProductionSemanticError("story must be Story or null")
        characters = tuple(self.characters)
        locations = tuple(self.locations)
        continuity = tuple(self.scene_continuity)
        if not all(isinstance(item, Character) for item in characters):
            raise ProductionSemanticError("characters must contain Character values")
        if not all(isinstance(item, Location) for item in locations):
            raise ProductionSemanticError("locations must contain Location values")
        if not all(isinstance(item, SceneContinuity) for item in continuity):
            raise ProductionSemanticError(
                "scene_continuity must contain SceneContinuity values"
            )

        character_ids = {item.character_id for item in characters}
        location_ids = {item.location_id for item in locations}
        continuity_ids = {item.scene_id for item in continuity}
        if len(character_ids) != len(characters):
            raise ProductionSemanticError("character_id values must be unique")
        if len(location_ids) != len(locations):
            raise ProductionSemanticError("location_id values must be unique")
        if len(continuity_ids) != len(continuity):
            raise ProductionSemanticError(
                "scene continuity values must be unique by scene_id"
            )
        for item in continuity:
            unknown_characters = set(item.character_ids).difference(character_ids)
            if unknown_characters:
                raise ProductionSemanticError(
                    f"scene {item.scene_id!r} continuity references unknown characters: "
                    f"{sorted(unknown_characters)!r}"
                )
            if item.location_id is not None and item.location_id not in location_ids:
                raise ProductionSemanticError(
                    f"scene {item.scene_id!r} continuity references unknown location "
                    f"{item.location_id!r}"
                )

        object.__setattr__(self, "characters", characters)
        object.__setattr__(self, "locations", locations)
        object.__setattr__(self, "scene_continuity", continuity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "document_kind": "micro_drama",
            "story": None if self.story is None else self.story.to_dict(),
            "characters": [item.to_dict() for item in self.characters],
            "locations": [item.to_dict() for item in self.locations],
            "scene_continuity": [item.to_dict() for item in self.scene_continuity],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MicroDramaDocument":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("micro-drama document must be a JSON object")
        allowed = {
            "schema_version",
            "document_kind",
            "story",
            "characters",
            "locations",
            "scene_continuity",
        }
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(
                f"unsupported micro-drama fields: {sorted(unknown)!r}"
            )
        if data.get("document_kind") != "micro_drama":
            raise ProductionSemanticError(
                "micro-drama document_kind must be 'micro_drama'"
            )
        story_data = data.get("story")
        raw_characters = data.get("characters", [])
        raw_locations = data.get("locations", [])
        raw_continuity = data.get("scene_continuity", [])
        if story_data is not None and not isinstance(story_data, Mapping):
            raise ProductionSemanticError("micro-drama story must be an object or null")
        if not isinstance(raw_characters, list):
            raise ProductionSemanticError("micro-drama characters must be a list")
        if not isinstance(raw_locations, list):
            raise ProductionSemanticError("micro-drama locations must be a list")
        if not isinstance(raw_continuity, list):
            raise ProductionSemanticError("micro-drama scene_continuity must be a list")
        return cls(
            schema_version=data.get("schema_version"),
            story=None if story_data is None else Story.from_dict(story_data),
            characters=tuple(Character.from_dict(item) for item in raw_characters),
            locations=tuple(Location.from_dict(item) for item in raw_locations),
            scene_continuity=tuple(
                SceneContinuity.from_dict(item) for item in raw_continuity
            ),
        )
