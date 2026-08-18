"""Secret-safe product diagnostics shared by API, launcher and support tools."""

from __future__ import annotations

import os
import platform
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

from uv_studio import __version__
from uv_studio.config import configuration_root, projects_root, user_data_root
from uv_studio.projects.maintenance import (
    ProjectMaintenanceError,
    verify_migration_recovery_snapshot,
)
from uv_studio.release_manifest import (
    REQUIRED_RELEASE_COMPONENT_IDS,
    ReleaseManifestError,
    load_release_manifest,
    verify_release_tree,
)
from uv_studio.system_resources import build_system_resource_snapshot

DIAGNOSTICS_SCHEMA_VERSION = 3
_RELEASE_ROOT_ENV = "UV_STUDIO_RELEASE_ROOT"
_MEDIA_COMPONENTS = {
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "melt": "mlt",
}
ToolLookup = Callable[[str], str | None]
PathResolver = Callable[[], Path]


def _configured_release_root() -> Path | None:
    raw = os.environ.get(_RELEASE_ROOT_ENV, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def _development_media_tools(tool_lookup: ToolLookup) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for executable in _MEDIA_COMPONENTS:
        resolved = tool_lookup(executable)
        result[executable] = {
            "available": bool(resolved),
            "source": "system_path" if resolved else "unavailable",
            "release_component": None,
        }
    return result


def _packaged_media_tools(
    release_root: Path,
    component_entrypoints: dict[str, str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for executable, component_id in _MEDIA_COMPONENTS.items():
        relative = component_entrypoints.get(component_id)
        available = False
        if relative is not None:
            candidate = release_root / relative
            try:
                available = candidate.is_file() and not candidate.is_symlink()
            except OSError:
                available = False
        result[executable] = {
            "available": available,
            "source": "release_manifest" if relative is not None else "unavailable",
            "release_component": component_id if relative is not None else None,
        }
    return result


def _probe_writable_directory(path: Path) -> tuple[bool, int | None]:
    marker: Path | None = None
    try:
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            return False, None
        free_bytes: int | None
        try:
            free_bytes = int(shutil.disk_usage(path).free)
        except OSError:
            free_bytes = None
        marker = path / f".uv-diagnostics-{uuid.uuid4().hex}.tmp"
        with marker.open("xb") as handle:
            handle.write(b"uv-studio-diagnostics\n")
            handle.flush()
            os.fsync(handle.fileno())
        marker.unlink()
        marker = None
        return True, free_bytes
    except OSError:
        return False, None
    finally:
        if marker is not None:
            try:
                marker.unlink(missing_ok=True)
            except OSError:
                pass


def _storage_self_check() -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    result: dict[str, Any] = {"probe_performed": True}
    roots: tuple[tuple[str, PathResolver], ...] = (
        ("user_data", user_data_root),
        ("project_store", projects_root),
        ("configuration", configuration_root),
    )

    for key, resolver in roots:
        try:
            path = resolver()
        except (OSError, RuntimeError):
            result[key] = {"writable": False, "free_bytes": None}
            issues.append(
                {
                    "code": f"storage.{key}_path_invalid",
                    "severity": "error",
                    "message": f"UV Studio {key.replace('_', ' ')} path is invalid.",
                }
            )
            continue

        writable, free_bytes = _probe_writable_directory(path)
        result[key] = {"writable": writable, "free_bytes": free_bytes}
        if not writable:
            issues.append(
                {
                    "code": f"storage.{key}_not_writable",
                    "severity": "error",
                    "message": f"UV Studio cannot write to its {key.replace('_', ' ')} directory.",
                }
            )
    return result, issues


def _empty_recovery_result(*, checked: bool) -> dict[str, Any]:
    return {
        "checked": checked,
        "snapshot_count": 0 if checked else None,
        "valid_snapshot_count": 0 if checked else None,
        "invalid_snapshot_count": 0 if checked else None,
        "incomplete_staging_count": 0 if checked else None,
        "latest_created_at": None,
    }


def _recovery_self_check() -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    try:
        root = user_data_root() / "recovery" / "migrations"
        if not root.exists():
            return _empty_recovery_result(checked=True), issues
        if root.is_symlink() or not root.is_dir():
            raise OSError("invalid recovery root")
        children = list(root.iterdir())
    except (OSError, RuntimeError):
        issues.append(
            {
                "code": "recovery.root_unreadable",
                "severity": "warning",
                "message": "UV Studio recovery metadata cannot be inspected.",
            }
        )
        result = _empty_recovery_result(checked=True)
        result["invalid_snapshot_count"] = None
        result["incomplete_staging_count"] = None
        return result, issues

    snapshots: list[Path] = []
    incomplete_staging = 0
    for item in children:
        if item.name.startswith("."):
            if item.name.endswith(".staging"):
                incomplete_staging += 1
            continue
        if item.is_dir() or item.is_symlink():
            snapshots.append(item)

    valid = 0
    invalid = 0
    created_at_values: list[str] = []
    for snapshot in snapshots:
        try:
            manifest = verify_migration_recovery_snapshot(snapshot)
        except (OSError, ProjectMaintenanceError):
            invalid += 1
            continue
        valid += 1
        created_at = manifest.get("created_at")
        if isinstance(created_at, str):
            created_at_values.append(created_at)

    if invalid:
        issues.append(
            {
                "code": "recovery.invalid_snapshots",
                "severity": "warning",
                "message": "One or more UV Studio migration recovery snapshots failed validation.",
            }
        )
    if incomplete_staging:
        issues.append(
            {
                "code": "recovery.incomplete_staging",
                "severity": "warning",
                "message": "UV Studio found an incomplete migration recovery staging set.",
            }
        )
    return {
        "checked": True,
        "snapshot_count": len(snapshots),
        "valid_snapshot_count": valid,
        "invalid_snapshot_count": invalid,
        "incomplete_staging_count": incomplete_staging,
        "latest_created_at": max(created_at_values, default=None),
    }, issues


def build_diagnostics(
    *,
    verify_release: bool = False,
    probe_storage: bool = False,
    tool_lookup: ToolLookup = shutil.which,
) -> dict[str, Any]:
    """Return diagnostics without provider credentials, environment dumps or absolute paths."""

    release_root = _configured_release_root()
    release: dict[str, Any] = {
        "configured": release_root is not None,
        "manifest_valid": None,
        "integrity": None,
        "product_version": None,
        "build_id": None,
        "target": None,
        "components": {},
        "problems": [],
    }
    mode = "packaged" if release_root is not None else "development"

    if release_root is None:
        media_tools = _development_media_tools(tool_lookup)
        overall_status = "ok" if all(item["available"] for item in media_tools.values()) else "degraded"
    else:
        component_entrypoints: dict[str, str] = {}
        try:
            manifest = load_release_manifest(release_root)
            release["manifest_valid"] = True
            release["product_version"] = manifest.product_version
            release["build_id"] = manifest.build_id
            release["target"] = {
                "os": manifest.target_os,
                "arch": manifest.target_arch,
            }
            release["components"] = {
                item.component_id: {
                    "version": item.version,
                    "entrypoint": item.entrypoint,
                }
                for item in manifest.components
            }
            component_entrypoints = {
                item.component_id: item.entrypoint for item in manifest.components
            }
            integrity = verify_release_tree(
                manifest,
                release_root,
                verify_hashes=verify_release,
            )
            release["integrity"] = integrity
            release["problems"] = list(integrity["problems"])
        except (OSError, ReleaseManifestError) as exc:
            release["manifest_valid"] = False
            release["integrity"] = {
                "ok": False,
                "verify_hashes": verify_release,
                "checked_files": 0,
                "problems": [str(exc)],
            }
            release["problems"] = [str(exc)]
        media_tools = _packaged_media_tools(release_root, component_entrypoints)
        overall_status = (
            "ok"
            if release["manifest_valid"] is True
            and isinstance(release["integrity"], dict)
            and release["integrity"].get("ok") is True
            and all(item["available"] for item in media_tools.values())
            else "invalid_release"
        )

    issues: list[dict[str, str]] = []
    storage: dict[str, Any] = {
        "probe_performed": False,
        "user_data": {"writable": None, "free_bytes": None},
        "project_store": {"writable": None, "free_bytes": None},
        "configuration": {"writable": None, "free_bytes": None},
    }
    recovery = _empty_recovery_result(checked=False)
    if probe_storage:
        storage, storage_issues = _storage_self_check()
        recovery, recovery_issues = _recovery_self_check()
        issues.extend(storage_issues)
        issues.extend(recovery_issues)
        if overall_status == "ok" and issues:
            overall_status = "degraded"

    expected_components = list(REQUIRED_RELEASE_COMPONENT_IDS)
    return {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "overall_status": overall_status,
        "mode": mode,
        "product_version": __version__,
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "os": platform.system().lower(),
            "architecture": platform.machine().lower(),
            "frozen": bool(getattr(sys, "frozen", False)),
        },
        "resources": build_system_resource_snapshot(),
        "release": release,
        "required_release_components": expected_components,
        "media_tools": media_tools,
        "storage": storage,
        "recovery": recovery,
        "issues": issues,
    }
