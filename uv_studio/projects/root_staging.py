"""Cross-runtime leases for transient Project Store root staging files.

Long-running publishers intentionally keep partial bytes outside canonical project
folders so archive/export can observe only durable project state. A hard process exit
must not leave those transient bytes forever, but another runtime must also never
mistake a live staging file for an orphan. Each staging path therefore owns a tiny
sidecar lease file whose OS byte-range/file lock is held for the staging lifetime.
Startup cleanup removes only exact UV-owned names whose lease can be acquired
non-blockingly, proving that no cooperating runtime still owns the staging path.
"""

from __future__ import annotations

import errno
import logging
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator

logger = logging.getLogger(__name__)

_HEX32 = r"[0-9a-f]{32}"
_SAFE_SUFFIX = re.compile(r"^(?:\.[A-Za-z0-9][A-Za-z0-9._-]*)?$")
_ROOT_STAGING_NAMES = (
    re.compile(rf"^\.uv-generation-attempt_{_HEX32}-{_HEX32}(?:\.[A-Za-z0-9][A-Za-z0-9._-]*)?$"),
    re.compile(rf"^\.uv-source-upload-src_{_HEX32}\.{_HEX32}\.upload$"),
    re.compile(rf"^\.uv-webvtt-sub_{_HEX32}-{_HEX32}\.vtt$"),
    re.compile(rf"^\.uv-ffconcat-{_HEX32}\.txt$"),
    re.compile(rf"^\.uv-timeline-assemble-art_{_HEX32}-{_HEX32}(?:\.[A-Za-z0-9][A-Za-z0-9._-]*)?$"),
)
_LEASE_SUFFIX = ".lease"


def _is_lock_contention(exc: OSError) -> bool:
    return (
        exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK, errno.EPERM}
        or getattr(exc, "winerror", None) in {32, 33, 36}
    )


def _try_acquire_os_lock(handle: BinaryIO) -> bool:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError as exc:
            if _is_lock_contention(exc):
                return False
            raise

    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EAGAIN}:
            return False
        raise


def _release_os_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _validate_root(root: Path) -> Path:
    root = Path(root)
    if root.is_symlink():
        raise OSError("Project Store root staging path must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise OSError("Project Store root staging path must be a directory")
    return root


def _validate_suffix(suffix: str) -> str:
    if not isinstance(suffix, str) or _SAFE_SUFFIX.fullmatch(suffix) is None:
        raise ValueError(f"unsafe root staging suffix: {suffix!r}")
    return suffix


def _validate_identity(value: str, *, prefix: str, field_name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(rf"{re.escape(prefix)}{_HEX32}", value) is None:
        raise ValueError(f"invalid {field_name}: {value!r}")
    return value


def _is_owned_staging_name(name: str) -> bool:
    return any(pattern.fullmatch(name) is not None for pattern in _ROOT_STAGING_NAMES)


@contextmanager
def _leased_path(root: Path, *, name_factory) -> Iterator[Path]:
    root = _validate_root(root)
    lease_handle: BinaryIO | None = None
    lease_path: Path | None = None
    staging_path: Path | None = None

    for _ in range(16):
        token = uuid.uuid4().hex
        name = name_factory(token)
        if not _is_owned_staging_name(name):  # pragma: no cover - factory invariant
            raise ValueError(f"root staging factory produced an unowned name: {name!r}")
        candidate = root / name
        candidate_lease = root / f"{name}{_LEASE_SUFFIX}"
        try:
            handle = candidate_lease.open("x+b")
        except FileExistsError:
            continue
        try:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
            if not _try_acquire_os_lock(handle):  # pragma: no cover - unique lease invariant
                raise OSError("new root staging lease was unexpectedly already locked")
            try:
                candidate.open("xb").close()
            except FileExistsError:
                _release_os_lock(handle)
                handle.close()
                candidate_lease.unlink(missing_ok=True)
                continue
        except Exception:
            if not handle.closed:
                try:
                    _release_os_lock(handle)
                except Exception:
                    pass
                handle.close()
            candidate_lease.unlink(missing_ok=True)
            raise
        lease_handle = handle
        lease_path = candidate_lease
        staging_path = candidate
        break

    if lease_handle is None or lease_path is None or staging_path is None:
        raise FileExistsError("could not allocate a unique UV root staging path")

    try:
        yield staging_path
    finally:
        try:
            staging_path.unlink(missing_ok=True)
        finally:
            try:
                _release_os_lock(lease_handle)
            finally:
                lease_handle.close()
                lease_path.unlink(missing_ok=True)


@contextmanager
def generation_root_staging(root: Path, attempt_id: str, suffix: str) -> Iterator[Path]:
    attempt_id = _validate_identity(attempt_id, prefix="attempt_", field_name="attempt_id")
    suffix = _validate_suffix(suffix)
    with _leased_path(
        root,
        name_factory=lambda token: f".uv-generation-{attempt_id}-{token}{suffix}",
    ) as path:
        yield path


@contextmanager
def source_upload_root_staging(root: Path, source_id: str) -> Iterator[Path]:
    source_id = _validate_identity(source_id, prefix="src_", field_name="source_id")
    with _leased_path(
        root,
        name_factory=lambda token: f".uv-source-upload-{source_id}.{token}.upload",
    ) as path:
        yield path


@contextmanager
def webvtt_root_staging(root: Path, artifact_id: str) -> Iterator[Path]:
    artifact_id = _validate_identity(artifact_id, prefix="sub_", field_name="artifact_id")
    with _leased_path(
        root,
        name_factory=lambda token: f".uv-webvtt-{artifact_id}-{token}.vtt",
    ) as path:
        yield path


@contextmanager
def ffconcat_root_staging(root: Path) -> Iterator[Path]:
    with _leased_path(
        root,
        name_factory=lambda token: f".uv-ffconcat-{token}.txt",
    ) as path:
        yield path


@contextmanager
def timeline_root_staging(root: Path, artifact_id: str, suffix: str) -> Iterator[Path]:
    artifact_id = _validate_identity(artifact_id, prefix="art_", field_name="artifact_id")
    suffix = _validate_suffix(suffix)
    with _leased_path(
        root,
        name_factory=lambda token: f".uv-timeline-assemble-{artifact_id}-{token}{suffix}",
    ) as path:
        yield path


def recover_stale_root_staging(root: Path) -> tuple[Path, ...]:
    """Remove only exact UV staging files whose sidecar lease proves no live owner.

    The scan is intentionally non-recursive. Unknown root files, project directories,
    symlinks, malformed/legacy staging names and currently locked leases are preserved.
    """

    root = _validate_root(root)
    recovered: list[Path] = []
    try:
        entries = tuple(root.iterdir())
    except OSError:
        raise

    for lease_path in sorted(entries, key=lambda item: item.name):
        if not lease_path.name.endswith(_LEASE_SUFFIX):
            continue
        staging_name = lease_path.name[: -len(_LEASE_SUFFIX)]
        if not _is_owned_staging_name(staging_name):
            continue
        if lease_path.is_symlink() or not lease_path.is_file():
            logger.error("unsafe UV root staging lease preserved: %s", lease_path.name)
            continue

        try:
            handle = lease_path.open("r+b")
        except FileNotFoundError:
            continue
        try:
            try:
                acquired = _try_acquire_os_lock(handle)
            except OSError as exc:
                logger.error("could not inspect UV root staging lease %s: %s", lease_path.name, exc)
                continue
            if not acquired:
                continue

            staging_path = root / staging_name
            remove_lease = False
            try:
                if staging_path.is_symlink():
                    logger.error("unsafe UV root staging symlink preserved: %s", staging_path.name)
                    continue
                if staging_path.exists() and not staging_path.is_file():
                    logger.error("unsafe UV root staging non-file preserved: %s", staging_path.name)
                    continue
                if staging_path.exists():
                    staging_path.unlink()
                    recovered.append(staging_path)
                    logger.warning("recovered stale UV root staging file: %s", staging_path.name)
                remove_lease = True
            finally:
                _release_os_lock(handle)
            if remove_lease:
                handle.close()
                lease_path.unlink(missing_ok=True)
                continue
        finally:
            if not handle.closed:
                handle.close()

    return tuple(recovered)
