"""Shared production-semantic contracts reused by rich Production Directions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from uv_studio.projects.models import ProjectValidationError, validate_identifier

PRODUCTION_SEMANTICS_SCHEMA_VERSION = 1
PRODUCTION_SEMANTICS_DOCUMENT_ID = "semantics"
PRODUCTION_SEMANTICS_PATH = "production/semantics.json"

_MAX_TEXT_LENGTH = 4000


class ProductionSemanticError(ProjectValidationError):
    """Shared Scene/Shot/Take state is malformed or inconsistent."""


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
    normalized = tuple(
        _identifier(item, field_name=f"{field_name} item")
        for item in value
    )
    if len(normalized) != len(set(normalized)):
        raise ProductionSemanticError(f"{field_name} values must be unique")
    return normalized


@dataclass(frozen=True)
class Scene:
    scene_id: str
    title: str
    summary: str = ""
    shot_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "scene_id", _identifier(self.scene_id, field_name="scene_id"))
        object.__setattr__(
            self,
            "title",
            _text(self.title, field_name="scene title", required=True, limit=500),
        )
        object.__setattr__(self, "summary", _text(self.summary, field_name="scene summary"))
        object.__setattr__(
            self,
            "shot_ids",
            _id_tuple(self.shot_ids, field_name="scene shot_ids"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "summary": self.summary,
            "shot_ids": list(self.shot_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Scene":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("scene must be a JSON object")
        allowed = {"scene_id", "title", "summary", "shot_ids"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(f"unsupported scene fields: {sorted(unknown)!r}")
        missing = {"scene_id", "title"}.difference(data)
        if missing:
            raise ProductionSemanticError(f"scene is missing fields: {sorted(missing)!r}")
        return cls(
            scene_id=data["scene_id"],
            title=data["title"],
            summary=data.get("summary", ""),
            shot_ids=tuple(data.get("shot_ids", [])),
        )


@dataclass(frozen=True)
class Shot:
    shot_id: str
    scene_id: str
    intent: str
    reference_ids: tuple[str, ...] = ()
    take_ids: tuple[str, ...] = ()
    accepted_take_id: str | None = None
    timeline_clip_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="shot_id"))
        object.__setattr__(self, "scene_id", _identifier(self.scene_id, field_name="shot scene_id"))
        object.__setattr__(
            self,
            "intent",
            _text(self.intent, field_name="shot intent", required=True),
        )
        object.__setattr__(
            self,
            "reference_ids",
            _id_tuple(self.reference_ids, field_name="shot reference_ids"),
        )
        object.__setattr__(
            self,
            "take_ids",
            _id_tuple(self.take_ids, field_name="shot take_ids"),
        )
        accepted = self.accepted_take_id
        if accepted is not None:
            accepted = _identifier(accepted, field_name="accepted_take_id")
        object.__setattr__(self, "accepted_take_id", accepted)
        object.__setattr__(
            self,
            "timeline_clip_ids",
            _id_tuple(self.timeline_clip_ids, field_name="shot timeline_clip_ids"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "scene_id": self.scene_id,
            "intent": self.intent,
            "reference_ids": list(self.reference_ids),
            "take_ids": list(self.take_ids),
            "accepted_take_id": self.accepted_take_id,
            "timeline_clip_ids": list(self.timeline_clip_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Shot":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("shot must be a JSON object")
        allowed = {
            "shot_id",
            "scene_id",
            "intent",
            "reference_ids",
            "take_ids",
            "accepted_take_id",
            "timeline_clip_ids",
        }
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(f"unsupported shot fields: {sorted(unknown)!r}")
        missing = {"shot_id", "scene_id", "intent"}.difference(data)
        if missing:
            raise ProductionSemanticError(f"shot is missing fields: {sorted(missing)!r}")
        return cls(
            shot_id=data["shot_id"],
            scene_id=data["scene_id"],
            intent=data["intent"],
            reference_ids=tuple(data.get("reference_ids", [])),
            take_ids=tuple(data.get("take_ids", [])),
            accepted_take_id=data.get("accepted_take_id"),
            timeline_clip_ids=tuple(data.get("timeline_clip_ids", [])),
        )


@dataclass(frozen=True)
class Take:
    take_id: str
    shot_id: str
    reference_id: str
    label: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "take_id", _identifier(self.take_id, field_name="take_id"))
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="take shot_id"))
        object.__setattr__(
            self,
            "reference_id",
            _identifier(self.reference_id, field_name="take reference_id"),
        )
        object.__setattr__(self, "label", _text(self.label, field_name="take label", limit=500))
        object.__setattr__(self, "notes", _text(self.notes, field_name="take notes"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "take_id": self.take_id,
            "shot_id": self.shot_id,
            "reference_id": self.reference_id,
            "label": self.label,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Take":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("take must be a JSON object")
        allowed = {"take_id", "shot_id", "reference_id", "label", "notes"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(f"unsupported take fields: {sorted(unknown)!r}")
        missing = {"take_id", "shot_id", "reference_id"}.difference(data)
        if missing:
            raise ProductionSemanticError(f"take is missing fields: {sorted(missing)!r}")
        return cls(
            take_id=data["take_id"],
            shot_id=data["shot_id"],
            reference_id=data["reference_id"],
            label=data.get("label", ""),
            notes=data.get("notes", ""),
        )


@dataclass(frozen=True)
class ProductionSemanticsDocument:
    scenes: tuple[Scene, ...] = ()
    shots: tuple[Shot, ...] = ()
    takes: tuple[Take, ...] = ()
    schema_version: int = PRODUCTION_SEMANTICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PRODUCTION_SEMANTICS_SCHEMA_VERSION:
            raise ProductionSemanticError(
                f"unsupported production semantics schema: {self.schema_version!r}; "
                f"supported={PRODUCTION_SEMANTICS_SCHEMA_VERSION}"
            )

        scenes = tuple(self.scenes)
        shots = tuple(self.shots)
        takes = tuple(self.takes)
        if not all(isinstance(item, Scene) for item in scenes):
            raise ProductionSemanticError("scenes must contain Scene values")
        if not all(isinstance(item, Shot) for item in shots):
            raise ProductionSemanticError("shots must contain Shot values")
        if not all(isinstance(item, Take) for item in takes):
            raise ProductionSemanticError("takes must contain Take values")

        scene_by_id = {item.scene_id: item for item in scenes}
        shot_by_id = {item.shot_id: item for item in shots}
        take_by_id = {item.take_id: item for item in takes}
        if len(scene_by_id) != len(scenes):
            raise ProductionSemanticError("scene_id values must be unique")
        if len(shot_by_id) != len(shots):
            raise ProductionSemanticError("shot_id values must be unique")
        if len(take_by_id) != len(takes):
            raise ProductionSemanticError("take_id values must be unique")

        linked_shots: set[str] = set()
        for scene in scenes:
            for shot_id in scene.shot_ids:
                shot = shot_by_id.get(shot_id)
                if shot is None:
                    raise ProductionSemanticError(
                        f"scene {scene.scene_id!r} references unknown shot {shot_id!r}"
                    )
                if shot.scene_id != scene.scene_id:
                    raise ProductionSemanticError(
                        f"shot {shot_id!r} belongs to scene {shot.scene_id!r}, "
                        f"not {scene.scene_id!r}"
                    )
                if shot_id in linked_shots:
                    raise ProductionSemanticError(
                        f"shot {shot_id!r} is linked from more than one scene"
                    )
                linked_shots.add(shot_id)
        if linked_shots != set(shot_by_id):
            missing = sorted(set(shot_by_id).difference(linked_shots))
            raise ProductionSemanticError(
                f"shots must be linked from their scene: {missing!r}"
            )

        linked_takes: set[str] = set()
        for shot in shots:
            if shot.scene_id not in scene_by_id:
                raise ProductionSemanticError(
                    f"shot {shot.shot_id!r} references unknown scene {shot.scene_id!r}"
                )
            for take_id in shot.take_ids:
                take = take_by_id.get(take_id)
                if take is None:
                    raise ProductionSemanticError(
                        f"shot {shot.shot_id!r} references unknown take {take_id!r}"
                    )
                if take.shot_id != shot.shot_id:
                    raise ProductionSemanticError(
                        f"take {take_id!r} belongs to shot {take.shot_id!r}, "
                        f"not {shot.shot_id!r}"
                    )
                if take_id in linked_takes:
                    raise ProductionSemanticError(
                        f"take {take_id!r} is linked from more than one shot"
                    )
                linked_takes.add(take_id)
            if (
                shot.accepted_take_id is not None
                and shot.accepted_take_id not in shot.take_ids
            ):
                raise ProductionSemanticError(
                    f"accepted take {shot.accepted_take_id!r} is not a candidate "
                    f"for shot {shot.shot_id!r}"
                )
        if linked_takes != set(take_by_id):
            missing = sorted(set(take_by_id).difference(linked_takes))
            raise ProductionSemanticError(
                f"takes must be linked from their shot: {missing!r}"
            )

        object.__setattr__(self, "scenes", scenes)
        object.__setattr__(self, "shots", shots)
        object.__setattr__(self, "takes", takes)

    def scene(self, scene_id: str) -> Scene:
        scene_id = _identifier(scene_id, field_name="scene_id")
        for item in self.scenes:
            if item.scene_id == scene_id:
                return item
        raise ProductionSemanticError(f"scene not found: {scene_id!r}")

    def shot(self, shot_id: str) -> Shot:
        shot_id = _identifier(shot_id, field_name="shot_id")
        for item in self.shots:
            if item.shot_id == shot_id:
                return item
        raise ProductionSemanticError(f"shot not found: {shot_id!r}")

    def take(self, take_id: str) -> Take:
        take_id = _identifier(take_id, field_name="take_id")
        for item in self.takes:
            if item.take_id == take_id:
                return item
        raise ProductionSemanticError(f"take not found: {take_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "document_kind": "production_semantics",
            "scenes": [item.to_dict() for item in self.scenes],
            "shots": [item.to_dict() for item in self.shots],
            "takes": [item.to_dict() for item in self.takes],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProductionSemanticsDocument":
        if not isinstance(data, Mapping):
            raise ProductionSemanticError("production semantics must be a JSON object")
        allowed = {"schema_version", "document_kind", "scenes", "shots", "takes"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProductionSemanticError(
                f"unsupported production semantics fields: {sorted(unknown)!r}"
            )
        if data.get("document_kind") != "production_semantics":
            raise ProductionSemanticError(
                "production semantics document_kind must be 'production_semantics'"
            )
        raw_scenes = data.get("scenes", [])
        raw_shots = data.get("shots", [])
        raw_takes = data.get("takes", [])
        if not isinstance(raw_scenes, list):
            raise ProductionSemanticError("production semantics scenes must be a list")
        if not isinstance(raw_shots, list):
            raise ProductionSemanticError("production semantics shots must be a list")
        if not isinstance(raw_takes, list):
            raise ProductionSemanticError("production semantics takes must be a list")
        return cls(
            schema_version=data.get("schema_version"),
            scenes=tuple(Scene.from_dict(item) for item in raw_scenes),
            shots=tuple(Shot.from_dict(item) for item in raw_shots),
            takes=tuple(Take.from_dict(item) for item in raw_takes),
        )
