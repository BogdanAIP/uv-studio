"""Current-byte verification for project-owned media at trust boundaries."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class MediaIntegrityError(ValueError):
    """Registered media bytes no longer match canonical identity metadata."""


@dataclass(frozen=True)
class VerifiedMediaIdentity:
    sha256: str
    size_bytes: int


def verify_registered_media_bytes(path: Path, metadata: Mapping[str, Any]) -> VerifiedMediaIdentity:
    expected_sha = metadata.get("sha256")
    expected_size = metadata.get("size_bytes")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        raise MediaIntegrityError("media metadata requires sha256")
    if isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size <= 0:
        raise MediaIntegrityError("media metadata requires positive size_bytes")
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
    if size != expected_size:
        raise MediaIntegrityError("registered media size no longer matches metadata")
    actual_sha = digest.hexdigest()
    if actual_sha != expected_sha:
        raise MediaIntegrityError("registered media sha256 no longer matches current file bytes")
    return VerifiedMediaIdentity(sha256=actual_sha, size_bytes=size)
