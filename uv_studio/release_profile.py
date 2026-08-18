"""Strict machine-readable Windows release input profile."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

RELEASE_PROFILE_SCHEMA_VERSION = 6
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ReleaseProfileError(ValueError):
    pass


def _object(value: Any, location: str, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ReleaseProfileError(f"{location} has unexpected fields")
    return value


def _string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ReleaseProfileError(f"{location} must be a non-empty canonical string")
    if "\r" in value or "\n" in value:
        raise ReleaseProfileError(f"{location} must not contain line breaks")
    return value


def _token(value: Any, location: str) -> str:
    raw = _string(value, location)
    if not _TOKEN_RE.fullmatch(raw):
        raise ReleaseProfileError(f"{location} must be a safe build-tool token")
    return raw


def _relative_path(value: Any, location: str) -> str:
    raw = _string(value, location)
    if "\\" in raw:
        raise ReleaseProfileError(f"{location} must use forward slashes")
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ReleaseProfileError(f"{location} must be a canonical relative path")
    if path.as_posix() != raw:
        raise ReleaseProfileError(f"{location} must be canonical")
    return raw


def _sha256(value: Any, location: str) -> str:
    raw = _string(value, location)
    if len(raw) != 64 or raw != raw.lower() or any(ch not in "0123456789abcdef" for ch in raw):
        raise ReleaseProfileError(f"{location} must be 64 lowercase hexadecimal characters")
    return raw


def _https_url(value: Any, location: str) -> str:
    raw = _string(value, location)
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise ReleaseProfileError(f"{location} must be an absolute credential-free HTTPS URL")
    return raw


def _download(value: Any, location: str) -> dict[str, Any]:
    download = _object(value, location, {"url", "sha256"})
    download["url"] = _https_url(download["url"], f"{location}.url")
    download["sha256"] = _sha256(download["sha256"], f"{location}.sha256")
    return download


def _chocolatey_acquisition(value: Any, location: str) -> dict[str, Any]:
    acquisition = _object(value, location, {"provider", "package", "package_version", "source"})
    acquisition["provider"] = _token(acquisition["provider"], f"{location}.provider")
    if acquisition["provider"] != "chocolatey":
        raise ReleaseProfileError(f"{location}.provider must be chocolatey")
    acquisition["package"] = _token(acquisition["package"], f"{location}.package")
    acquisition["package_version"] = _token(acquisition["package_version"], f"{location}.package_version")
    acquisition["source"] = _https_url(acquisition["source"], f"{location}.source")
    return acquisition


def load_release_profile(path: Path | str) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseProfileError("release profile is not readable valid JSON") from exc
    root = _object(raw, "release profile", {"schema_version", "target", "python", "node", "media", "build_tools"})
    if root["schema_version"] != RELEASE_PROFILE_SCHEMA_VERSION or isinstance(root["schema_version"], bool):
        raise ReleaseProfileError(f"release profile schema_version must be integer {RELEASE_PROFILE_SCHEMA_VERSION}")

    target = _object(root["target"], "target", {"os", "arch"})
    if target != {"os": "windows", "arch": "x86_64"}:
        raise ReleaseProfileError("release profile target must be windows/x86_64")

    python = _object(root["python"], "python", {"version", "constraints"})
    python["version"] = _string(python["version"], "python.version")
    python["constraints"] = _relative_path(python["constraints"], "python.constraints")

    node = _object(root["node"], "node", {"version", "lock", "download"})
    node["version"] = _string(node["version"], "node.version")
    node["lock"] = _relative_path(node["lock"], "node.lock")
    node["download"] = _download(node["download"], "node.download")

    media = _object(
        root["media"],
        "media",
        {"distribution", "version", "download", "corresponding_source"},
    )
    media["distribution"] = _string(media["distribution"], "media.distribution")
    media["version"] = _string(media["version"], "media.version")
    media["download"] = _download(media["download"], "media.download")
    media["corresponding_source"] = _download(
        media["corresponding_source"], "media.corresponding_source"
    )

    build_tools = _object(root["build_tools"], "build_tools", {"pyinstaller", "nsis"})
    build_tools["pyinstaller"] = _string(build_tools["pyinstaller"], "build_tools.pyinstaller")
    nsis = _object(
        build_tools["nsis"],
        "build_tools.nsis",
        {"version", "acquisition", "corresponding_source"},
    )
    nsis["version"] = _string(nsis["version"], "build_tools.nsis.version")
    nsis["acquisition"] = _chocolatey_acquisition(nsis["acquisition"], "build_tools.nsis.acquisition")
    nsis["corresponding_source"] = _download(
        nsis["corresponding_source"], "build_tools.nsis.corresponding_source"
    )
    return root
