"""Strict, product-owned manifest for immutable UV Studio release payloads."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

RELEASE_MANIFEST_SCHEMA_VERSION = 1
RELEASE_MANIFEST_FILENAME = "release-manifest.json"
REQUIRED_RELEASE_COMPONENT_IDS = (
    "backend",
    "frontend",
    "node",
    "desktop",
    "ffmpeg",
    "ffprobe",
    "mlt",
)
_ALLOWED_TARGET_OS = frozenset({"windows"})
_ALLOWED_TARGET_ARCH = frozenset({"x86_64", "arm64"})


class ReleaseManifestError(ValueError):
    """Release manifest or payload violates the product-owned release contract."""


def _require_object(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReleaseManifestError(f"{location} must be a JSON object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], *, location: str, expected: set[str]
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected.difference(actual))
        extra = sorted(actual.difference(expected))
        detail: list[str] = []
        if missing:
            detail.append(f"missing={missing!r}")
        if extra:
            detail.append(f"extra={extra!r}")
        raise ReleaseManifestError(
            f"{location} has unexpected fields" + (f": {', '.join(detail)}" if detail else "")
        )


def _require_nonblank_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseManifestError(f"{location} must be a non-empty string")
    if value != value.strip():
        raise ReleaseManifestError(f"{location} must not contain surrounding whitespace")
    return value


def _portable_relative_path(value: Any, location: str) -> str:
    raw = _require_nonblank_string(value, location)
    if "\\" in raw:
        raise ReleaseManifestError(f"{location} must use forward slashes")
    path = PurePosixPath(raw)
    parts = path.parts
    if path.is_absolute() or not parts:
        raise ReleaseManifestError(f"{location} must be relative")
    if any(part in {"", ".", ".."} for part in parts):
        raise ReleaseManifestError(f"{location} contains an invalid path segment")
    if any(":" in part for part in parts):
        raise ReleaseManifestError(f"{location} contains a Windows-unsafe ':' path segment")
    canonical = path.as_posix()
    if canonical != raw:
        raise ReleaseManifestError(f"{location} must be canonical")
    if canonical == RELEASE_MANIFEST_FILENAME:
        raise ReleaseManifestError(
            f"{location} must not point at the release manifest itself"
        )
    return canonical


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ReleaseFile:
    path: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_dict(cls, raw: Any, *, location: str) -> "ReleaseFile":
        value = _require_object(raw, location)
        _require_exact_keys(
            value,
            location=location,
            expected={"path", "size_bytes", "sha256"},
        )
        path = _portable_relative_path(value["path"], f"{location}.path")
        size_bytes = value["size_bytes"]
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
            raise ReleaseManifestError(f"{location}.size_bytes must be a non-negative integer")
        sha256 = _require_nonblank_string(value["sha256"], f"{location}.sha256").lower()
        if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
            raise ReleaseManifestError(f"{location}.sha256 must be exactly 64 hexadecimal characters")
        return cls(path=path, size_bytes=size_bytes, sha256=sha256)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class ReleaseComponent:
    component_id: str
    version: str
    entrypoint: str

    @classmethod
    def from_dict(cls, raw: Any, *, location: str) -> "ReleaseComponent":
        value = _require_object(raw, location)
        _require_exact_keys(
            value,
            location=location,
            expected={"component_id", "version", "entrypoint"},
        )
        component_id = _require_nonblank_string(
            value["component_id"], f"{location}.component_id"
        )
        if component_id not in REQUIRED_RELEASE_COMPONENT_IDS:
            raise ReleaseManifestError(
                f"{location}.component_id is unsupported: {component_id!r}"
            )
        return cls(
            component_id=component_id,
            version=_require_nonblank_string(value["version"], f"{location}.version"),
            entrypoint=_portable_relative_path(
                value["entrypoint"], f"{location}.entrypoint"
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "component_id": self.component_id,
            "version": self.version,
            "entrypoint": self.entrypoint,
        }


@dataclass(frozen=True)
class ReleaseManifest:
    product_name: str
    product_version: str
    build_id: str
    target_os: str
    target_arch: str
    components: tuple[ReleaseComponent, ...]
    files: tuple[ReleaseFile, ...]
    schema_version: int = RELEASE_MANIFEST_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, raw: Any) -> "ReleaseManifest":
        root = _require_object(raw, "root")
        _require_exact_keys(
            root,
            location="root",
            expected={"schema_version", "product", "target", "components", "files"},
        )
        if isinstance(root["schema_version"], bool) or root["schema_version"] != RELEASE_MANIFEST_SCHEMA_VERSION:
            raise ReleaseManifestError(
                f"schema_version must be integer {RELEASE_MANIFEST_SCHEMA_VERSION}"
            )

        product = _require_object(root["product"], "product")
        _require_exact_keys(
            product,
            location="product",
            expected={"name", "version", "build_id"},
        )
        product_name = _require_nonblank_string(product["name"], "product.name")
        if product_name != "UV Studio":
            raise ReleaseManifestError("product.name must be exactly 'UV Studio'")

        target = _require_object(root["target"], "target")
        _require_exact_keys(target, location="target", expected={"os", "arch"})
        target_os = _require_nonblank_string(target["os"], "target.os")
        target_arch = _require_nonblank_string(target["arch"], "target.arch")
        if target_os not in _ALLOWED_TARGET_OS:
            raise ReleaseManifestError(f"unsupported release target OS: {target_os!r}")
        if target_arch not in _ALLOWED_TARGET_ARCH:
            raise ReleaseManifestError(f"unsupported release target architecture: {target_arch!r}")

        raw_components = root["components"]
        if not isinstance(raw_components, list) or not raw_components:
            raise ReleaseManifestError("components must be a non-empty JSON array")
        components = tuple(
            ReleaseComponent.from_dict(item, location=f"components[{index}]")
            for index, item in enumerate(raw_components)
        )
        component_ids = [item.component_id for item in components]
        if len(component_ids) != len(set(component_ids)):
            raise ReleaseManifestError("components must not contain duplicate component_id values")
        if set(component_ids) != set(REQUIRED_RELEASE_COMPONENT_IDS):
            raise ReleaseManifestError(
                "components must contain the exact required release component set"
            )

        raw_files = root["files"]
        if not isinstance(raw_files, list) or not raw_files:
            raise ReleaseManifestError("files must be a non-empty JSON array")
        files = tuple(
            ReleaseFile.from_dict(item, location=f"files[{index}]")
            for index, item in enumerate(raw_files)
        )
        file_paths = [item.path for item in files]
        if len(file_paths) != len(set(file_paths)):
            raise ReleaseManifestError("files must not contain duplicate paths")
        if tuple(file_paths) != tuple(sorted(file_paths)):
            raise ReleaseManifestError("files must be sorted by canonical path")
        inventory = set(file_paths)
        missing_entrypoints = sorted(
            item.entrypoint for item in components if item.entrypoint not in inventory
        )
        if missing_entrypoints:
            raise ReleaseManifestError(
                "component entrypoints are missing from the release file inventory: "
                + ", ".join(missing_entrypoints)
            )

        return cls(
            product_name=product_name,
            product_version=_require_nonblank_string(product["version"], "product.version"),
            build_id=_require_nonblank_string(product["build_id"], "product.build_id"),
            target_os=target_os,
            target_arch=target_arch,
            components=components,
            files=files,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "product": {
                "name": self.product_name,
                "version": self.product_version,
                "build_id": self.build_id,
            },
            "target": {"os": self.target_os, "arch": self.target_arch},
            "components": [item.to_dict() for item in self.components],
            "files": [item.to_dict() for item in self.files],
        }


def _release_files(root: Path) -> tuple[Path, ...]:
    try:
        resolved_root = root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise ReleaseManifestError("release root could not be resolved") from exc
    if not resolved_root.is_dir() or resolved_root.is_symlink():
        raise ReleaseManifestError("release root must be a real directory, not a symlink")

    files: list[Path] = []
    for current, dirs, names in os.walk(resolved_root, followlinks=False):
        current_path = Path(current)
        for directory in dirs:
            candidate = current_path / directory
            if candidate.is_symlink():
                raise ReleaseManifestError(
                    f"release payload must not contain symlink directories: {candidate.relative_to(resolved_root).as_posix()}"
                )
        for name in names:
            candidate = current_path / name
            relative = candidate.relative_to(resolved_root).as_posix()
            if relative == RELEASE_MANIFEST_FILENAME:
                continue
            if candidate.is_symlink():
                raise ReleaseManifestError(
                    f"release payload must not contain symlink files: {relative}"
                )
            if not candidate.is_file():
                raise ReleaseManifestError(
                    f"release payload contains a non-regular file: {relative}"
                )
            files.append(candidate)
    return tuple(sorted(files, key=lambda item: item.relative_to(resolved_root).as_posix()))


def build_release_manifest(
    release_root: Path | str,
    *,
    product_version: str,
    build_id: str,
    target_arch: str,
    components: Iterable[ReleaseComponent | Mapping[str, Any]],
) -> ReleaseManifest:
    root = Path(release_root).expanduser().resolve(strict=True)
    inventory = tuple(
        ReleaseFile(
            path=path.relative_to(root).as_posix(),
            size_bytes=path.stat().st_size,
            sha256=_sha256_file(path),
        )
        for path in _release_files(root)
    )
    normalized_components = tuple(
        item
        if isinstance(item, ReleaseComponent)
        else ReleaseComponent.from_dict(item, location=f"components[{index}]")
        for index, item in enumerate(components)
    )
    candidate = ReleaseManifest(
        product_name="UV Studio",
        product_version=_require_nonblank_string(product_version, "product.version"),
        build_id=_require_nonblank_string(build_id, "product.build_id"),
        target_os="windows",
        target_arch=target_arch,
        components=normalized_components,
        files=inventory,
    )
    return ReleaseManifest.from_dict(candidate.to_dict())


def write_release_manifest(
    manifest: ReleaseManifest, release_root: Path | str
) -> Path:
    root = Path(release_root).expanduser().resolve(strict=True)
    target = root / RELEASE_MANIFEST_FILENAME
    if target.exists() and target.is_symlink():
        raise ReleaseManifestError("release manifest path must not be a symlink")
    temp = root / f".{RELEASE_MANIFEST_FILENAME}.{uuid.uuid4().hex}.tmp"
    serialized = json.dumps(
        manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return target


def load_release_manifest(release_root: Path | str) -> ReleaseManifest:
    root = Path(release_root).expanduser().resolve(strict=True)
    path = root / RELEASE_MANIFEST_FILENAME
    try:
        if not path.is_file() or path.is_symlink():
            raise ReleaseManifestError("release manifest is missing or is not a regular file")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except ReleaseManifestError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError("release manifest could not be read as valid JSON") from exc
    return ReleaseManifest.from_dict(raw)


def verify_release_tree(
    manifest: ReleaseManifest,
    release_root: Path | str,
    *,
    verify_hashes: bool,
) -> dict[str, Any]:
    root = Path(release_root).expanduser().resolve(strict=True)
    problems: list[str] = []
    expected = {item.path: item for item in manifest.files}

    try:
        actual_paths = {
            path.relative_to(root).as_posix(): path for path in _release_files(root)
        }
    except ReleaseManifestError as exc:
        return {
            "ok": False,
            "verify_hashes": verify_hashes,
            "checked_files": 0,
            "problems": [str(exc)],
        }

    extra = sorted(set(actual_paths).difference(expected))
    missing = sorted(set(expected).difference(actual_paths))
    if extra:
        problems.append("unlisted release files: " + ", ".join(extra[:8]))
    if missing:
        problems.append("missing release files: " + ", ".join(missing[:8]))

    checked = 0
    for relative in sorted(set(expected).intersection(actual_paths)):
        specification = expected[relative]
        path = actual_paths[relative]
        try:
            size_bytes = path.stat().st_size
        except OSError as exc:
            problems.append(f"could not stat release file {relative}: {exc}")
            continue
        checked += 1
        if size_bytes != specification.size_bytes:
            problems.append(
                f"size mismatch for {relative}: expected {specification.size_bytes}, got {size_bytes}"
            )
            continue
        if verify_hashes:
            try:
                actual_sha256 = _sha256_file(path)
            except OSError as exc:
                problems.append(f"could not hash release file {relative}: {exc}")
                continue
            if actual_sha256 != specification.sha256:
                problems.append(f"sha256 mismatch for {relative}")

    return {
        "ok": not problems,
        "verify_hashes": verify_hashes,
        "checked_files": checked,
        "problems": problems,
    }
