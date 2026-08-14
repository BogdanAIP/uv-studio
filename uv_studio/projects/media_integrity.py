"""Current-byte verification for project-owned media at trust boundaries."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .models import ProjectReference
from .store import ProjectStore


class MediaIntegrityError(ValueError):
    """Registered media bytes no longer match canonical identity metadata."""


@dataclass(frozen=True)
class VerifiedMediaIdentity:
    sha256: str
    size_bytes: int


def measure_media_identity(path: Path) -> VerifiedMediaIdentity:
    """Hash one regular file while rejecting mutation during the measurement."""
    if not path.is_file() or path.is_symlink():
        raise MediaIntegrityError("registered media must be a regular non-symlink file")

    before = path.stat()
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    after = path.stat()

    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns or size != after.st_size:
        raise MediaIntegrityError("registered media changed while its identity was being verified")
    return VerifiedMediaIdentity(sha256=digest.hexdigest(), size_bytes=size)


def verify_registered_media_bytes(path: Path, metadata: Mapping[str, Any]) -> VerifiedMediaIdentity:
    expected_sha = metadata.get("sha256")
    expected_size = metadata.get("size_bytes")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        raise MediaIntegrityError("media metadata requires sha256")
    if isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size <= 0:
        raise MediaIntegrityError("media metadata requires positive size_bytes")

    identity = measure_media_identity(path)
    if identity.size_bytes != expected_size:
        raise MediaIntegrityError("registered media size no longer matches metadata")
    if identity.sha256 != expected_sha:
        raise MediaIntegrityError("registered media sha256 no longer matches current file bytes")
    return identity


def verify_project_media_path(
    project_store: ProjectStore,
    project_id: str,
    relative_path: str,
    path: Path,
) -> ProjectReference:
    """Resolve one canonical media identity by path and verify its current bytes."""
    project = project_store.load_project(project_id)
    matches = [
        reference
        for reference in (*project.sources, *project.artifacts)
        if reference.path == relative_path
    ]
    if len(matches) != 1:
        raise MediaIntegrityError(
            f"render input {relative_path!r} must have exactly one registered project media identity"
        )
    reference = matches[0]
    verify_registered_media_bytes(path, reference.metadata)
    return reference
