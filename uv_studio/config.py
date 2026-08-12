"""UV Studio-owned machine/runtime settings.

Portable project state never reads credentials or host-only configuration from
this module. Machine configuration lives under the UV Studio configuration root,
not inside the vendored VideoClaw source tree or canonical Project Store.
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


def projects_root() -> Path:
    configured = os.environ.get("UV_STUDIO_PROJECTS_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_PROJECTS_ROOT.resolve()


def _validate_configuration_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == VENDOR_ROOT or VENDOR_ROOT in resolved.parents:
        raise RuntimeError("UV Studio machine configuration must not live inside vendor/")
    project_store = projects_root()
    if resolved == project_store or project_store in resolved.parents:
        raise RuntimeError(
            "UV Studio machine configuration must not live inside the canonical Project Store"
        )
    return resolved


def configuration_root() -> Path:
    configured = os.environ.get("UV_STUDIO_CONFIG_DIR", "").strip()
    if configured:
        return _validate_configuration_root(Path(configured))
    return _validate_configuration_root(DEFAULT_CONFIGURATION_ROOT)


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
