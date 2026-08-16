"""Trusted executable resolution for development and immutable packaged releases."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Callable

from uv_studio.config import release_root
from uv_studio.release_manifest import (
    RELEASE_MANIFEST_FILENAME,
    ReleaseManifestError,
    load_release_manifest,
    verify_release_tree,
)

ToolLookup = Callable[[str], str | None]

_PACKAGED_TOOL_COMPONENTS = {
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "melt": "mlt",
    "node": "node",
}


class ToolchainResolutionError(RuntimeError):
    """A required executable cannot be resolved through the trusted runtime boundary."""


def _manifest_cache_key(root: Path) -> tuple[str, int, int]:
    manifest = root / RELEASE_MANIFEST_FILENAME
    try:
        stat = manifest.stat()
    except OSError as exc:
        raise ToolchainResolutionError("packaged release manifest is not readable") from exc
    return str(root), stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=8)
def _deep_verified_component_paths(
    root_text: str,
    manifest_mtime_ns: int,
    manifest_size: int,
) -> dict[str, str]:
    del manifest_mtime_ns, manifest_size
    root = Path(root_text)
    try:
        manifest = load_release_manifest(root)
        integrity = verify_release_tree(manifest, root, verify_hashes=True)
    except (OSError, ReleaseManifestError) as exc:
        raise ToolchainResolutionError(str(exc)) from exc
    if not integrity["ok"]:
        detail = "; ".join(str(item) for item in integrity["problems"][:4])
        raise ToolchainResolutionError(
            "packaged release integrity verification failed"
            + (f": {detail}" if detail else "")
        )

    paths: dict[str, str] = {}
    for component in manifest.components:
        candidate = root / component.entrypoint
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise ToolchainResolutionError(
                f"packaged component {component.component_id!r} entrypoint is unreadable"
            ) from exc
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ToolchainResolutionError(
                f"packaged component {component.component_id!r} escaped release root"
            ) from exc
        if not resolved.is_file() or resolved.is_symlink():
            raise ToolchainResolutionError(
                f"packaged component {component.component_id!r} entrypoint is not a regular file"
            )
        paths[component.component_id] = str(resolved)
    return paths


def clear_toolchain_cache() -> None:
    """Test/update hook; normal product processes verify one immutable payload per run."""

    _deep_verified_component_paths.cache_clear()


def packaged_component_paths() -> dict[str, str]:
    root = release_root()
    if root is None:
        raise ToolchainResolutionError("UV Studio is not running from a packaged release")
    return dict(_deep_verified_component_paths(*_manifest_cache_key(root)))


def packaged_tool_paths() -> dict[str, str]:
    components = packaged_component_paths()
    result: dict[str, str] = {}
    for tool, component_id in _PACKAGED_TOOL_COMPONENTS.items():
        path = components.get(component_id)
        if not path:
            raise ToolchainResolutionError(
                f"packaged release is missing required component {component_id!r}"
            )
        result[tool] = path
    return result


def resolve_tool(
    name: str,
    *,
    explicit: str | os.PathLike[str] | None = None,
    lookup: ToolLookup = shutil.which,
) -> str:
    """Resolve one executable without allowing system PATH to shadow packaged tools."""

    if name not in _PACKAGED_TOOL_COMPONENTS:
        raise ToolchainResolutionError(f"unsupported product-owned executable: {name!r}")

    root = release_root()
    if root is None:
        if explicit is not None:
            try:
                candidate = Path(explicit).expanduser().resolve(strict=True)
            except OSError as exc:
                raise ToolchainResolutionError(f"configured {name} could not be resolved") from exc
            if not candidate.is_file() or candidate.is_symlink():
                raise ToolchainResolutionError(f"configured {name} is not a regular file")
            return str(candidate)
        discovered = lookup(name)
        if not discovered:
            raise ToolchainResolutionError(f"{name} is not available in this installation")
        return discovered

    trusted = packaged_tool_paths()[name]
    if explicit is not None:
        try:
            configured = str(Path(explicit).expanduser().resolve(strict=True))
        except OSError as exc:
            raise ToolchainResolutionError(f"configured {name} could not be resolved") from exc
        if os.path.normcase(configured) != os.path.normcase(trusted):
            raise ToolchainResolutionError(
                f"packaged {name} override does not match the verified release component"
            )
    return trusted


def local_ffmpeg_tool_overrides() -> dict[str, str] | None:
    """Return exact facade injection only in packaged mode; dev keeps existing lookup behavior."""

    if release_root() is None:
        return None
    tools = packaged_tool_paths()
    return {"ffmpeg": tools["ffmpeg"], "ffprobe": tools["ffprobe"]}
