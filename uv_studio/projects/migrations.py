"""Schema-version boundary for UV Studio project metadata."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .models import PROJECT_SCHEMA_VERSION, ProjectCompatibility, ProjectValidationError


class UnsupportedProjectSchema(ProjectValidationError):
    pass


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Move legacy top-level recipe identity into explicit compatibility state."""

    if "recipe_id" not in data:
        raise ProjectValidationError("schema-v1 project is missing recipe_id")
    if "compatibility" in data:
        raise ProjectValidationError(
            "schema-v1 project contains reserved compatibility state and cannot be migrated safely"
        )

    compatibility = ProjectCompatibility(recipe_id=data.pop("recipe_id"))
    data["compatibility"] = compatibility.to_dict()
    data["schema_version"] = 2
    return data


def migrate_project_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return project data upgraded to the current schema.

    Historical bytes are never rewritten by this function. Callers receive a
    detached current-schema mapping, while the original schema-v1 project can
    remain on disk until a later canonical write deliberately persists v2.
    """
    if not isinstance(data, Mapping):
        raise ProjectValidationError("project document must be a JSON object")
    if "schema_version" not in data:
        raise ProjectValidationError("project document has no schema_version")

    version = data["schema_version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise ProjectValidationError("schema_version must be an integer")
    if version < 1:
        raise UnsupportedProjectSchema(f"invalid project schema version: {version}")
    if version > PROJECT_SCHEMA_VERSION:
        raise UnsupportedProjectSchema(
            f"project schema v{version} is newer than supported v{PROJECT_SCHEMA_VERSION}"
        )

    current = deepcopy(dict(data))
    while version < PROJECT_SCHEMA_VERSION:
        migration = _MIGRATIONS.get(version)
        if migration is None:
            raise UnsupportedProjectSchema(
                f"no migration path from project schema v{version}"
            )
        current = migration(current)
        version = current.get("schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ProjectValidationError("migration produced invalid schema_version")

    return current


# Maps source version -> function that returns the next version.
_MIGRATIONS: dict[int, Any] = {
    1: _migrate_v1_to_v2,
}
