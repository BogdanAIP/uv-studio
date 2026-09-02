"""Canonical UV Studio project schema.

The schema is intentionally small. Specialized workflows store their own data
under `extensions` or dedicated project files instead of making every project
carry film/music/continuity fields.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Mapping

PROJECT_SCHEMA_VERSION = 2
PROJECT_COMPATIBILITY_SCHEMA_VERSION = 1
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:/")
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


def validate_timestamp(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProjectValidationError(f"{field_name} is required")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ProjectValidationError(f"{field_name} must be ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ProjectValidationError(f"{field_name} must include a timezone")
    return value


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
    if path.is_absolute() or _WINDOWS_DRIVE_RE.match(normalized) or ".." in path.parts:
        raise ProjectValidationError(f"reference path must stay inside the project: {value!r}")
    if any(part in {"", "."} for part in path.parts):
        raise ProjectValidationError(f"reference path is not canonical: {value!r}")
    return path.as_posix()


def _json_value(
    value: Any,
    *,
    field_name: str,
    _containers: set[int] | None = None,
) -> Any:
    """Return a detached, portable-JSON value or reject it.

    Canonical project state accepts only the value types JSON itself supports:
    objects with string keys, arrays, strings, booleans, null, integers and
    finite floating-point numbers. Python-only containers/objects are rejected
    rather than silently rewritten into a different value.
    """

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProjectValidationError(f"{field_name} must not contain NaN or Infinity")
        return value

    containers = _containers if _containers is not None else set()
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in containers:
            raise ProjectValidationError(f"{field_name} must not contain recursive containers")
        containers.add(marker)
        try:
            result: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ProjectValidationError(
                        f"{field_name} JSON object keys must be strings; got {key!r}"
                    )
                child_name = f"{field_name}.{key}" if key else field_name
                result[key] = _json_value(
                    item,
                    field_name=child_name,
                    _containers=containers,
                )
            return result
        finally:
            containers.remove(marker)

    if isinstance(value, list):
        marker = id(value)
        if marker in containers:
            raise ProjectValidationError(f"{field_name} must not contain recursive containers")
        containers.add(marker)
        try:
            return [
                _json_value(
                    item,
                    field_name=f"{field_name}[{index}]",
                    _containers=containers,
                )
                for index, item in enumerate(value)
            ]
        finally:
            containers.remove(marker)

    raise ProjectValidationError(
        f"{field_name} contains non-JSON value of type {type(value).__name__}"
    )


def _json_object(value: Mapping[str, Any] | None, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ProjectValidationError(f"{field_name} must be a JSON object")
    validated = _json_value(value, field_name=field_name)
    if not isinstance(validated, dict):
        raise ProjectValidationError(f"{field_name} must be a JSON object")
    return validated


def _validate_generation_reference_shape(path: str, metadata: Mapping[str, Any]) -> None:
    """Fail closed on structurally impossible UV Generation ProjectReferences.

    ``metadata.generation`` is already treated as reserved UV Generation authority by
    archive/recovery code. Its canonical path and continuation lineage therefore
    belong to the Project persistence boundary too, including crash-left attempts
    that are not yet durably ``SUCCEEDED`` and cannot use the stronger Job authority
    validator yet.
    """

    generation = metadata.get("generation")
    if not isinstance(generation, Mapping):
        return

    attempt_id = generation.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        raise ProjectValidationError("Generation reference requires a non-empty attempt_id")

    parts = PurePosixPath(path).parts
    if len(parts) != 2 or parts[0] != "artifacts":
        raise ProjectValidationError(
            "Generation artifact path must be a direct file under the canonical artifacts root"
        )
    expected_name = f"generated_{attempt_id}"
    if not (parts[1] == expected_name or parts[1].startswith(expected_name + ".")):
        raise ProjectValidationError("Generation artifact path must match its attempt_id")

    contract = generation.get("contract")
    if not isinstance(contract, Mapping):
        raise ProjectValidationError("Generation reference requires generation.contract")
    continuation = contract.get("continuation_source_reference_id")
    if continuation is None:
        expected_lineage = None
    elif isinstance(continuation, str) and continuation:
        expected_lineage = {
            "kind": "continuation",
            "source_reference_id": continuation,
        }
    else:
        raise ProjectValidationError(
            "Generation contract continuation_source_reference_id must be null or non-empty text"
        )
    if generation.get("lineage") != expected_lineage:
        raise ProjectValidationError("Generation reference lineage disagrees with its contract")


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
        path = validate_project_relative_path(self.path)
        metadata = _json_object(self.metadata, field_name="metadata")
        _validate_generation_reference_shape(path, metadata)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "metadata", metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "path": self.path,
            "metadata": _json_object(self.metadata, field_name="metadata"),
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
class ProjectCompatibility:
    """Persisted compatibility-only identity for pre-product Project callers.

    ``recipe_id`` is retained exactly so historical recipe projects remain
    readable, but schema v2 no longer stores it as top-level canonical product
    identity. Modern product identity remains owned by ``extensions.studio``.
    """

    recipe_id: str
    schema_version: int = PROJECT_COMPATIBILITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != PROJECT_COMPATIBILITY_SCHEMA_VERSION
        ):
            raise ProjectValidationError(
                f"unsupported Project compatibility schema: {self.schema_version!r}; "
                f"supported={PROJECT_COMPATIBILITY_SCHEMA_VERSION}"
            )
        object.__setattr__(
            self,
            "recipe_id",
            validate_identifier(self.recipe_id, field_name="compatibility.recipe_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recipe_id": self.recipe_id,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProjectCompatibility":
        if not isinstance(data, Mapping):
            raise ProjectValidationError("compatibility must be a JSON object")
        allowed = {"schema_version", "recipe_id"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise ProjectValidationError(
                f"unsupported Project compatibility fields: {sorted(unknown)!r}"
            )
        missing = allowed.difference(data)
        if missing:
            raise ProjectValidationError(
                f"Project compatibility is missing fields: {sorted(missing)!r}"
            )
        return cls(
            schema_version=data["schema_version"],
            recipe_id=data["recipe_id"],
        )


@dataclass(frozen=True)
class ProjectDocument:
    project_id: str
    title: str
    # Compatibility-only in-memory alias. Schema v2 persists this under
    # compatibility.recipe_id rather than as top-level canonical identity.
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
            self,
            "recipe_id",
            ProjectCompatibility(recipe_id=self.recipe_id).recipe_id,
        )
        if not isinstance(self.title, str) or not self.title.strip():
            raise ProjectValidationError("title must be a non-empty string")
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(
            self, "created_at", validate_timestamp(self.created_at, field_name="created_at")
        )
        object.__setattr__(
            self, "updated_at", validate_timestamp(self.updated_at, field_name="updated_at")
        )
        object.__setattr__(self, "settings", _json_object(self.settings, field_name="settings"))
        object.__setattr__(self, "extensions", _json_object(self.extensions, field_name="extensions"))
        object.__setattr__(self, "sources", self._validated_references(self.sources))
        object.__setattr__(self, "artifacts", self._validated_references(self.artifacts))
        self._validate_unique_reference_ids()

    @staticmethod
    def _validated_references(
        values: tuple[ProjectReference, ...] | list[ProjectReference],
    ) -> tuple[ProjectReference, ...]:
        validated: list[ProjectReference] = []
        for reference in values:
            if not isinstance(reference, ProjectReference):
                raise ProjectValidationError("sources/artifacts must contain ProjectReference values")
            validated.append(
                ProjectReference(
                    id=reference.id,
                    kind=reference.kind,
                    path=reference.path,
                    metadata=reference.metadata,
                )
            )
        return tuple(validated)

    def _validate_unique_reference_ids(self) -> None:
        seen: set[str] = set()
        for reference in (*self.sources, *self.artifacts):
            if reference.id in seen:
                raise ProjectValidationError(f"duplicate reference id: {reference.id}")
            seen.add(reference.id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "title": self.title,
            "compatibility": ProjectCompatibility(recipe_id=self.recipe_id).to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": _json_object(self.settings, field_name="settings"),
            "sources": [item.to_dict() for item in self.sources],
            "artifacts": [item.to_dict() for item in self.artifacts],
            "extensions": _json_object(self.extensions, field_name="extensions"),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectDocument":
        if not isinstance(data, Mapping):
            raise ProjectValidationError("project document must be a JSON object")
        required = [
            "schema_version",
            "project_id",
            "title",
            "compatibility",
            "created_at",
            "updated_at",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ProjectValidationError(f"missing project fields: {', '.join(missing)}")
        if "recipe_id" in data:
            raise ProjectValidationError(
                "schema-v2 project must not contain top-level recipe_id; "
                "use compatibility.recipe_id"
            )
        compatibility = ProjectCompatibility.from_mapping(data["compatibility"])
        return cls(
            schema_version=int(data["schema_version"]),
            project_id=str(data["project_id"]),
            title=str(data["title"]),
            recipe_id=compatibility.recipe_id,
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
            settings=_json_object(data.get("settings"), field_name="settings"),
            sources=tuple(ProjectReference.from_dict(item) for item in data.get("sources", [])),
            artifacts=tuple(ProjectReference.from_dict(item) for item in data.get("artifacts", [])),
            extensions=_json_object(data.get("extensions"), field_name="extensions"),
        )


def compatibility_recipe_id(project: ProjectDocument) -> str:
    """Return legacy recipe identity through the explicit compatibility boundary."""

    if not isinstance(project, ProjectDocument):
        raise ProjectValidationError("compatibility recipe lookup requires ProjectDocument")
    return ProjectCompatibility(recipe_id=project.recipe_id).recipe_id
