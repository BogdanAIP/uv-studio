"""Canonical UV Studio project schema.

The schema is intentionally small. Specialized workflows store their own data
under `extensions` or dedicated project files instead of making every project
carry film/music/continuity fields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Mapping

PROJECT_SCHEMA_VERSION = 1
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_ALLOWED_REFERENCE_KINDS = {
    "source",
    "asset",
    "artifact",
    "audio",
    "image",
    "video",
    "subtitle",
    "timeline",
    "document",
    "other",
}


class ProjectValidationError(ValueError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_identifier(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ProjectValidationError(
            f"{field_name} must match {_ID_RE.pattern!r}; got {value!r}"
        )
    return value


def validate_project_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectValidationError("reference path must be a non-empty string")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ProjectValidationError(f"reference path must stay inside the project: {value!r}")
    if any(part in {"", "."} for part in path.parts):
        raise ProjectValidationError(f"reference path is not canonical: {value!r}")
    return path.as_posix()


def _json_object(value: Mapping[str, Any] | None, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ProjectValidationError(f"{field_name} must be a JSON object")
    return dict(value)


@dataclass(frozen=True)
class ProjectReference:
    id: str
    kind: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", validate_identifier(self.id, field_name="reference id"))
        if self.kind not in _ALLOWED_REFERENCE_KINDS:
            raise ProjectValidationError(f"unsupported reference kind: {self.kind!r}")
        object.__setattr__(self, "path", validate_project_relative_path(self.path))
        object.__setattr__(self, "metadata", _json_object(self.metadata, field_name="metadata"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "path": self.path,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectReference":
        if not isinstance(data, Mapping):
            raise ProjectValidationError("reference must be a JSON object")
        try:
            return cls(
                id=str(data["id"]),
                kind=str(data["kind"]),
                path=str(data["path"]),
                metadata=_json_object(data.get("metadata"), field_name="metadata"),
            )
        except KeyError as exc:
            raise ProjectValidationError(f"missing reference field: {exc.args[0]}") from exc


@dataclass(frozen=True)
class ProjectDocument:
    project_id: str
    title: str
    recipe_id: str
    created_at: str
    updated_at: str
    settings: dict[str, Any] = field(default_factory=dict)
    sources: tuple[ProjectReference, ...] = ()
    artifacts: tuple[ProjectReference, ...] = ()
    extensions: dict[str, Any] = field(default_factory=dict)
    schema_version: int = PROJECT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROJECT_SCHEMA_VERSION:
            raise ProjectValidationError(
                f"ProjectDocument only represents schema v{PROJECT_SCHEMA_VERSION}; "
                f"got v{self.schema_version}"
            )
        object.__setattr__(
            self, "project_id", validate_identifier(self.project_id, field_name="project_id")
        )
        object.__setattr__(
            self, "recipe_id", validate_identifier(self.recipe_id, field_name="recipe_id")
        )
        if not isinstance(self.title, str) or not self.title.strip():
            raise ProjectValidationError("title must be a non-empty string")
        object.__setattr__(self, "title", self.title.strip())
        if not isinstance(self.created_at, str) or not self.created_at:
            raise ProjectValidationError("created_at is required")
        if not isinstance(self.updated_at, str) or not self.updated_at:
            raise ProjectValidationError("updated_at is required")
        object.__setattr__(self, "settings", _json_object(self.settings, field_name="settings"))
        object.__setattr__(self, "extensions", _json_object(self.extensions, field_name="extensions"))
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        self._validate_unique_reference_ids()

    def _validate_unique_reference_ids(self) -> None:
        seen: set[str] = set()
        for reference in (*self.sources, *self.artifacts):
            if not isinstance(reference, ProjectReference):
                raise ProjectValidationError("sources/artifacts must contain ProjectReference values")
            if reference.id in seen:
                raise ProjectValidationError(f"duplicate reference id: {reference.id}")
            seen.add(reference.id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "title": self.title,
            "recipe_id": self.recipe_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": dict(self.settings),
            "sources": [item.to_dict() for item in self.sources],
            "artifacts": [item.to_dict() for item in self.artifacts],
            "extensions": dict(self.extensions),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectDocument":
        if not isinstance(data, Mapping):
            raise ProjectValidationError("project document must be a JSON object")
        required = [
            "schema_version",
            "project_id",
            "title",
            "recipe_id",
            "created_at",
            "updated_at",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ProjectValidationError(f"missing project fields: {', '.join(missing)}")
        return cls(
            schema_version=int(data["schema_version"]),
            project_id=str(data["project_id"]),
            title=str(data["title"]),
            recipe_id=str(data["recipe_id"]),
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
            settings=_json_object(data.get("settings"), field_name="settings"),
            sources=tuple(ProjectReference.from_dict(item) for item in data.get("sources", [])),
            artifacts=tuple(ProjectReference.from_dict(item) for item in data.get("artifacts", [])),
            extensions=_json_object(data.get("extensions"), field_name="extensions"),
        )
