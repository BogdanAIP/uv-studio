"""Secret-safe, UV Studio-owned machine runtime configuration.

This configuration is deliberately separate from portable project state and from
`vendor/videoclaw-app/backend/config.yaml`. Public settings and provider secrets
are persisted separately under the ignored UV Studio machine configuration root.
The public read API never needs to deserialize a secret into its response model.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .config import runtime_config_path, runtime_secrets_path


class RuntimeConfigError(ValueError):
    """Machine runtime configuration is malformed or violates a safety boundary."""


SECRET_PATHS = (
    "api_providers.openai.api_key",
    "api_providers.gemini.api_key",
    "api_providers.deepseek.api_key",
    "api_providers.dashscope.api_key",
    "api_providers.ark.api_key",
    "api_providers.kling.api_key",
)

DEFAULT_RUNTIME_CONFIG: dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
        "log_level": "INFO",
        "access_log": False,
    },
    "api_providers": {
        "common": {
            "print_model_input": False,
            "proxy": "",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "enable_proxy": False,
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "enable_proxy": False,
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "enable_proxy": False,
        },
        "dashscope": {
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "enable_proxy": False,
        },
        "ark": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "enable_proxy": False,
        },
        "kling": {
            "base_url": "https://api-beijing.klingai.com",
            "enable_proxy": False,
        },
    },
    "models": {
        "llm": "qwen3.5-plus",
        "vlm": "qwen3.5-plus",
        "image_it2i": "doubao-seedream-5-0-260128",
        "image_t2i": "doubao-seedream-5-0-260128",
        "video": "wan2.7-i2v",
        "video_first_frame": "wan2.7-i2v",
        "video_start_end": "wan2.7-i2v",
        "video_reference": "wan2.7-r2v",
    },
    "generation": {
        "style": "realistic",
        "video_ratio": "16:9",
        "video_resolution": "720P",
        "video_generation_mode": "first_frame",
    },
}

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _validate_url(value: str, *, path: str) -> str:
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeConfigError(f"{path} must be an http(s) URL")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeConfigError(f"{path} must not contain URL userinfo credentials")
    if parsed.query or parsed.fragment:
        raise RuntimeConfigError(f"{path} must not contain query or fragment data")
    return normalized


def _validate_leaf(path: str, value: Any, default: Any) -> Any:
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise RuntimeConfigError(f"{path} must be a boolean")
        return value
    if isinstance(default, int) and not isinstance(default, bool):
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeConfigError(f"{path} must be an integer")
        if path == "server.port" and not 1 <= value <= 65535:
            raise RuntimeConfigError("server.port must be between 1 and 65535")
        return value
    if isinstance(default, str):
        if not isinstance(value, str):
            raise RuntimeConfigError(f"{path} must be a string")
        normalized = value.strip()
        if path == "server.host":
            if normalized not in _LOOPBACK_HOSTS:
                raise RuntimeConfigError("server.host must remain a loopback host")
            return normalized
        if path == "server.log_level":
            normalized = normalized.upper()
            if normalized not in _LOG_LEVELS:
                raise RuntimeConfigError("server.log_level is unsupported")
            return normalized
        if path.endswith(".base_url"):
            return _validate_url(normalized, path=path)
        if path == "api_providers.common.proxy":
            return "" if not normalized else _validate_url(normalized, path=path)
        return normalized
    raise RuntimeConfigError(f"unsupported runtime configuration schema at {path}")


def _validate_partial(
    values: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    prefix: str = "",
) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        raise RuntimeConfigError("runtime configuration must be a JSON object")
    validated: dict[str, Any] = {}
    for key, value in values.items():
        if not isinstance(key, str) or key not in schema:
            location = f"{prefix}.{key}" if prefix else str(key)
            raise RuntimeConfigError(f"unknown runtime configuration field: {location}")
        path = f"{prefix}.{key}" if prefix else key
        default = schema[key]
        if isinstance(default, Mapping):
            if not isinstance(value, Mapping):
                raise RuntimeConfigError(f"{path} must be a JSON object")
            validated[key] = _validate_partial(value, default, prefix=path)
        else:
            validated[key] = _validate_leaf(path, value, default)
    return validated


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeConfigError(f"invalid machine configuration file: {path.name}") from exc
    if not isinstance(raw, dict):
        raise RuntimeConfigError(f"machine configuration file must contain an object: {path.name}")
    return raw


def _atomic_write_json(path: Path, data: Mapping[str, Any], *, secret: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    serialized = json.dumps(dict(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        if secret:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
        else:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(temp, path)
        if secret:
            try:
                os.chmod(path, 0o600)
            except OSError:
                # Windows ACLs are inherited from the machine-local configuration
                # directory; chmod is only an additional best-effort restriction.
                pass
    except Exception:
        temp.unlink(missing_ok=True)
        raise


class RuntimeConfigStore:
    """Thread-safe public settings + write-only provider secret storage."""

    def __init__(
        self,
        *,
        config_path: Path | None = None,
        secrets_path: Path | None = None,
    ) -> None:
        self.config_path = (config_path or runtime_config_path()).expanduser().resolve()
        self.secrets_path = (secrets_path or runtime_secrets_path()).expanduser().resolve()
        if self.config_path == self.secrets_path:
            raise RuntimeConfigError("public runtime config and secret storage must be separate files")
        self._lock = threading.RLock()

    def public_config(self) -> dict[str, Any]:
        with self._lock:
            stored = _read_json_object(self.config_path)
            validated = _validate_partial(stored, DEFAULT_RUNTIME_CONFIG)
            return _deep_merge(DEFAULT_RUNTIME_CONFIG, validated)

    def _secrets(self) -> dict[str, str]:
        raw = _read_json_object(self.secrets_path)
        secrets: dict[str, str] = {}
        for path, value in raw.items():
            if path not in SECRET_PATHS:
                raise RuntimeConfigError("secret storage contains an unknown secret field")
            if not isinstance(value, str) or not value:
                raise RuntimeConfigError("secret storage contains an invalid secret value")
            secrets[path] = value
        return secrets

    def secret_status(self) -> dict[str, bool]:
        with self._lock:
            secrets = self._secrets()
            return {path: path in secrets for path in SECRET_PATHS}

    def update(
        self,
        *,
        values: Mapping[str, Any] | None = None,
        secret_updates: Mapping[str, str | None] | None = None,
    ) -> tuple[dict[str, Any], dict[str, bool]]:
        values = values or {}
        secret_updates = secret_updates or {}
        if not isinstance(values, Mapping):
            raise RuntimeConfigError("values must be a JSON object")
        if not isinstance(secret_updates, Mapping):
            raise RuntimeConfigError("secret_updates must be a JSON object")

        validated_values = _validate_partial(values, DEFAULT_RUNTIME_CONFIG)
        normalized_secret_updates: dict[str, str | None] = {}
        for path, value in secret_updates.items():
            if path not in SECRET_PATHS:
                raise RuntimeConfigError("unknown provider secret field")
            if value is None:
                normalized_secret_updates[path] = None
                continue
            if not isinstance(value, str) or not value.strip():
                raise RuntimeConfigError(
                    "secret replacement must be a non-empty string; use null to clear explicitly"
                )
            normalized_secret_updates[path] = value.strip()

        with self._lock:
            current_public = self.public_config()
            updated_public = _deep_merge(current_public, validated_values)
            # Validate the complete result again so manually edited stored files
            # cannot preserve an invalid value outside the submitted partial tree.
            updated_public = _deep_merge(
                DEFAULT_RUNTIME_CONFIG,
                _validate_partial(updated_public, DEFAULT_RUNTIME_CONFIG),
            )

            current_secrets = self._secrets()
            updated_secrets = dict(current_secrets)
            for path, value in normalized_secret_updates.items():
                if value is None:
                    updated_secrets.pop(path, None)
                else:
                    updated_secrets[path] = value

            if updated_public != current_public or not self.config_path.exists():
                _atomic_write_json(self.config_path, updated_public, secret=False)
            if updated_secrets != current_secrets or (
                normalized_secret_updates and not self.secrets_path.exists()
            ):
                _atomic_write_json(self.secrets_path, updated_secrets, secret=True)

            status = {path: path in updated_secrets for path in SECRET_PATHS}
            return copy.deepcopy(updated_public), status

    def secret_value(self, path: str) -> str | None:
        """Resolve one secret for an exact future adapter; never expose via HTTP."""
        if path not in SECRET_PATHS:
            raise RuntimeConfigError("unknown provider secret field")
        with self._lock:
            return self._secrets().get(path)
