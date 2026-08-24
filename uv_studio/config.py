"""UV Studio-owned machine/runtime settings.

Portable project state never reads credentials or host-only configuration from
this module. Development checkouts keep their historical repository-local data
root, while packaged releases move mutable state outside the immutable app
payload and into a user-owned data root.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = (ROOT / "vendor").resolve()
DEFAULT_PROJECTS_ROOT = ROOT / "data" / "projects"
DEFAULT_CONFIGURATION_ROOT = ROOT / "data" / "config"
DEFAULT_ALLOWED_FRONTEND_ORIGINS = (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
)


def release_root() -> Path | None:
    """Return the configured immutable packaged-app root, if this is a release run."""

    configured = os.environ.get("UV_STUDIO_RELEASE_ROOT", "").strip()
    if not configured:
        return None
    return Path(configured).expanduser().resolve()


def packaged_mode() -> bool:
    return release_root() is not None


def user_data_root() -> Path:
    """Return mutable packaged-app state root without consulting repository paths.

    `UV_STUDIO_USER_DATA_DIR` is the explicit portable/admin override. On Windows
    the launcher inherits LOCALAPPDATA, so the default becomes
    `%LOCALAPPDATA%/UV Studio`. XDG/home fallbacks keep diagnostics/tests portable.
    """

    configured = os.environ.get("UV_STUDIO_USER_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return (Path(local_app_data).expanduser() / "UV Studio").resolve()
    xdg_data_home = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg_data_home:
        return (Path(xdg_data_home).expanduser() / "uv-studio").resolve()
    return (Path.home() / ".local" / "share" / "uv-studio").resolve()


def paths_overlap(left: Path, right: Path) -> bool:
    left_resolved = left.expanduser().resolve()
    right_resolved = right.expanduser().resolve()
    return (
        left_resolved == right_resolved
        or left_resolved in right_resolved.parents
        or right_resolved in left_resolved.parents
    )


def validate_mutable_path(path: Path, *, label: str) -> Path:
    """Reject mutable machine state that could overwrite trusted application code."""

    resolved = path.expanduser().resolve()
    if paths_overlap(resolved, VENDOR_ROOT):
        raise RuntimeError(f"{label} must not overlap vendor/")
    packaged_root = release_root()
    if packaged_root is not None and paths_overlap(resolved, packaged_root):
        raise RuntimeError(f"{label} must not overlap the immutable UV Studio release payload")
    return resolved


def _projects_candidate() -> Path:
    configured = os.environ.get("UV_STUDIO_PROJECTS_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    if packaged_mode():
        return user_data_root() / "projects"
    return DEFAULT_PROJECTS_ROOT


def _configuration_candidate() -> Path:
    configured = os.environ.get("UV_STUDIO_CONFIG_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    if packaged_mode():
        return user_data_root() / "config"
    return DEFAULT_CONFIGURATION_ROOT


def projects_root() -> Path:
    resolved = validate_mutable_path(
        _projects_candidate(), label="UV Studio canonical Project Store"
    )
    configuration = validate_mutable_path(
        _configuration_candidate(), label="UV Studio machine configuration"
    )
    if paths_overlap(resolved, configuration):
        raise RuntimeError(
            "UV Studio canonical Project Store must not overlap machine configuration"
        )
    return resolved


def configuration_root() -> Path:
    resolved = validate_mutable_path(
        _configuration_candidate(), label="UV Studio machine configuration"
    )
    project_store = validate_mutable_path(
        _projects_candidate(), label="UV Studio canonical Project Store"
    )
    if paths_overlap(resolved, project_store):
        raise RuntimeError(
            "UV Studio machine configuration must not overlap the canonical Project Store"
        )
    return resolved


def runtime_config_path() -> Path:
    return configuration_root() / "runtime.json"


def runtime_secrets_path() -> Path:
    return configuration_root() / "secrets.json"


def allowed_frontend_origins() -> tuple[str, ...]:
    """Return explicit browser origins allowed to call the local backend directly.

    The Next.js development frontend normally uses same-origin rewrites, so CORS
    is compatibility support rather than the primary transport. Wildcards are
    deliberately rejected because the backend also exposes mutating local APIs.
    """

    raw = os.environ.get("UV_STUDIO_ALLOWED_ORIGINS", "").strip()
    candidates = (
        [item.strip() for item in raw.split(",") if item.strip()]
        if raw
        else list(DEFAULT_ALLOWED_FRONTEND_ORIGINS)
    )
    origins: list[str] = []
    for origin in candidates:
        if origin == "*":
            raise RuntimeError("UV_STUDIO_ALLOWED_ORIGINS must not contain '*'")
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"invalid UV Studio frontend origin: {origin!r}")
        if parsed.username is not None or parsed.password is not None:
            raise RuntimeError("UV Studio frontend origins must not contain userinfo")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise RuntimeError(f"UV Studio frontend origin must not contain a path/query: {origin!r}")
        canonical = f"{parsed.scheme}://{parsed.netloc}"
        if canonical not in origins:
            origins.append(canonical)
    if not origins:
        raise RuntimeError("UV Studio requires at least one explicit frontend origin")
    return tuple(origins)
