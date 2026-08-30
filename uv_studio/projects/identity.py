"""Typed UV Studio product identity over Project compatibility metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from uv_studio.production.directions import ProductionDirectionNotFound, get_production_direction
from uv_studio.projects.models import (
    ProjectDocument,
    ProjectValidationError,
    compatibility_recipe_id,
)

STUDIO_COMPAT_RECIPE_ID = "studio_v2"
STUDIO_EXTENSION_KEY = "studio"
# Version 1 is the first typed identity contract. It is intentionally independent
# from the product label "Studio v2".
STUDIO_IDENTITY_SCHEMA_VERSION = 1
STUDIO_PRODUCT_MODEL = "production_directions"

LEGACY_STUDIO_FIRST_SCHEMA_VERSION = 1
LEGACY_STUDIO_FIRST_PRODUCT_MODEL = "studio_first"
PR63_PRODUCTION_DIRECTIONS_SCHEMA_VERSION = 2

ProjectIdentityKind = Literal["modern_direction", "legacy_compatibility", "invalid_recovery"]
CompatibilityKind = Literal[
    "recipe",
    "studio_first",
    "studio_unversioned",
    "production_directions_v2",
]


class StudioIdentityError(ProjectValidationError):
    """Project metadata cannot be interpreted as a safe Studio identity."""


@dataclass(frozen=True)
class StudioProjectIdentity:
    """Exact modern Studio identity stored under ``extensions.studio``."""

    direction_id: str
    schema_version: int = STUDIO_IDENTITY_SCHEMA_VERSION
    product_model: str = STUDIO_PRODUCT_MODEL

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != STUDIO_IDENTITY_SCHEMA_VERSION
        ):
            raise StudioIdentityError(
                f"unsupported Studio identity schema: {self.schema_version!r}; "
                f"supported={STUDIO_IDENTITY_SCHEMA_VERSION}"
            )
        if self.product_model != STUDIO_PRODUCT_MODEL:
            raise StudioIdentityError(f"unsupported Studio product_model: {self.product_model!r}")
        if not isinstance(self.direction_id, str) or not self.direction_id:
            raise StudioIdentityError("Studio direction_id must be non-empty text")
        try:
            get_production_direction(self.direction_id)
        except ProductionDirectionNotFound as exc:
            raise StudioIdentityError(str(exc)) from exc

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "StudioProjectIdentity":
        if not isinstance(data, Mapping):
            raise StudioIdentityError("extensions.studio must be a JSON object")
        allowed = {"schema_version", "product_model", "direction_id"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise StudioIdentityError(f"unsupported Studio identity fields: {sorted(unknown)!r}")
        missing = allowed.difference(data)
        if missing:
            raise StudioIdentityError(f"Studio identity is missing fields: {sorted(missing)!r}")
        return cls(
            schema_version=data["schema_version"],
            product_model=data["product_model"],
            direction_id=data["direction_id"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "product_model": self.product_model,
            "direction_id": self.direction_id,
        }


@dataclass(frozen=True)
class ProjectIdentityProjection:
    """Backend-owned classification exposed to API/UI callers."""

    kind: ProjectIdentityKind
    direction_id: str | None = None
    compatibility_kind: CompatibilityKind | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "direction_id": self.direction_id,
            "compatibility_kind": self.compatibility_kind,
            "reason": self.reason,
        }


def studio_project_extensions(direction_id: str) -> dict[str, Any]:
    return {STUDIO_EXTENSION_KEY: StudioProjectIdentity(direction_id=direction_id).to_dict()}


def _is_legacy_studio_first(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {"schema_version", "product_model"}
        and value.get("schema_version") == LEGACY_STUDIO_FIRST_SCHEMA_VERSION
        and value.get("product_model") == LEGACY_STUDIO_FIRST_PRODUCT_MODEL
    )


def _pr63_direction_v2(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    if set(value) != {"schema_version", "product_model", "direction_id"}:
        return None
    if value.get("schema_version") != PR63_PRODUCTION_DIRECTIONS_SCHEMA_VERSION:
        return None
    if value.get("product_model") != STUDIO_PRODUCT_MODEL:
        return None
    direction_id = value.get("direction_id")
    if not isinstance(direction_id, str) or not direction_id:
        return None
    try:
        get_production_direction(direction_id)
    except ProductionDirectionNotFound:
        return None
    return direction_id


def classify_project_identity(project: ProjectDocument) -> ProjectIdentityProjection:
    recipe_id = compatibility_recipe_id(project)
    has_studio = STUDIO_EXTENSION_KEY in project.extensions
    raw_studio = project.extensions.get(STUDIO_EXTENSION_KEY)

    if not has_studio:
        if recipe_id == STUDIO_COMPAT_RECIPE_ID:
            return ProjectIdentityProjection(
                kind="legacy_compatibility",
                compatibility_kind="studio_unversioned",
                reason=(
                    "Studio compatibility project has no Production Direction identity; "
                    "an explicit migration is required before direction-domain commands"
                ),
            )
        return ProjectIdentityProjection(
            kind="legacy_compatibility",
            compatibility_kind="recipe",
            reason=f"legacy recipe project: {recipe_id}",
        )

    if recipe_id != STUDIO_COMPAT_RECIPE_ID:
        return ProjectIdentityProjection(
            kind="invalid_recovery",
            reason=(
                "extensions.studio is present but compatibility.recipe_id is not the neutral "
                f"{STUDIO_COMPAT_RECIPE_ID!r} compatibility value"
            ),
        )

    if _is_legacy_studio_first(raw_studio):
        return ProjectIdentityProjection(
            kind="legacy_compatibility",
            compatibility_kind="studio_first",
            reason=(
                "pre-Production-Directions Studio project; explicit migration is required "
                "before direction-domain commands"
            ),
        )

    pr63_direction = _pr63_direction_v2(raw_studio)
    if pr63_direction is not None:
        return ProjectIdentityProjection(
            kind="modern_direction",
            direction_id=pr63_direction,
        )

    if not isinstance(raw_studio, Mapping):
        return ProjectIdentityProjection(kind="invalid_recovery", reason="extensions.studio must be a JSON object")

    try:
        identity = StudioProjectIdentity.from_mapping(raw_studio)
    except StudioIdentityError as exc:
        return ProjectIdentityProjection(kind="invalid_recovery", reason=str(exc))

    return ProjectIdentityProjection(kind="modern_direction", direction_id=identity.direction_id)


def require_valid_project_identity(project: ProjectDocument) -> ProjectIdentityProjection:
    projection = classify_project_identity(project)
    if projection.kind == "invalid_recovery":
        raise StudioIdentityError(projection.reason or "invalid Studio project identity")
    return projection


def require_modern_studio_identity(project: ProjectDocument) -> StudioProjectIdentity:
    projection = classify_project_identity(project)
    if projection.kind != "modern_direction":
        raise StudioIdentityError(
            projection.reason or "project does not have a valid modern Production Direction identity"
        )
    raw = project.extensions[STUDIO_EXTENSION_KEY]
    assert isinstance(raw, Mapping)
    pr63_direction = _pr63_direction_v2(raw)
    if pr63_direction is not None:
        # PR #63 created this exact, already-valid Production Direction shape.
        # Normalize its typed view without rewriting portable project bytes.
        return StudioProjectIdentity(direction_id=pr63_direction)
    return StudioProjectIdentity.from_mapping(raw)


def _has_protected_studio_claim(project: ProjectDocument) -> bool:
    return (
        compatibility_recipe_id(project) == STUDIO_COMPAT_RECIPE_ID
        or STUDIO_EXTENSION_KEY in project.extensions
    )


def assert_project_identity_transition(current: ProjectDocument, proposed: ProjectDocument) -> None:
    """Block generic writes from creating, repairing or changing Studio identity."""

    if not (_has_protected_studio_claim(current) or _has_protected_studio_claim(proposed)):
        return
    current_has_studio = STUDIO_EXTENSION_KEY in current.extensions
    proposed_has_studio = STUDIO_EXTENSION_KEY in proposed.extensions
    if (
        compatibility_recipe_id(current) != compatibility_recipe_id(proposed)
        or current_has_studio != proposed_has_studio
        or current.extensions.get(STUDIO_EXTENSION_KEY) != proposed.extensions.get(STUDIO_EXTENSION_KEY)
    ):
        raise StudioIdentityError(
            "generic project mutation cannot change Studio product identity; "
            "use an explicit Studio identity migration command"
        )
