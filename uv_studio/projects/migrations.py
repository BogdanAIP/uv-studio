"""Schema-version boundary for UV Studio project metadata."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .models import PROJECT_SCHEMA_VERSION, ProjectValidationError


class UnsupportedProjectSchema(ProjectValidationError):
    pass


def migrate_project_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return project data upgraded to the current schema.

    Version 1 is the first schema, so no migration functions exist yet. Keeping
    this boundary from day one prevents future code from silently treating old
    or newer project files as if they matched the current model.
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
        if not isinstance(version, int):
            raise ProjectValidationError("migration produced invalid schema_version")

    return current


# Maps source version -> function that returns the next version.
_MIGRATIONS: dict[int, Any] = {}
