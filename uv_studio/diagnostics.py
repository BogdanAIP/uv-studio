"""Secret-safe product diagnostics shared by API, launcher and support tools."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

from uv_studio import __version__
from uv_studio.release_manifest import (
    REQUIRED_RELEASE_COMPONENT_IDS,
    ReleaseManifestError,
    load_release_manifest,
    verify_release_tree,
)

DIAGNOSTICS_SCHEMA_VERSION = 1
_RELEASE_ROOT_ENV = "UV_STUDIO_RELEASE_ROOT"
_MEDIA_COMPONENTS = {
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "melt": "mlt",
}
ToolLookup = Callable[[str], str | None]


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


def build_diagnostics(
    *,
    verify_release: bool = False,
    tool_lookup: ToolLookup = shutil.which,
) -> dict[str, Any]:
    """Return diagnostics without provider credentials, environment dumps or absolute tool paths."""

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
        "release": release,
        "required_release_components": expected_components,
        "media_tools": media_tools,
    }
