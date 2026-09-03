"""Cross-runtime leases for transient Project Store root staging files.

Long-running publishers intentionally keep partial bytes outside canonical project
folders so archive/export can observe only durable project state. A hard process exit
must not leave those transient bytes forever, but another runtime must also never
mistake a live staging file for an orphan. Each staging path therefore owns a tiny
sidecar lease file whose OS byte-range/file lock is held for the staging lifetime.
Startup cleanup removes only exact UV-owned names whose lease can be acquired
nonblockingly, proving that no cooperating runtime still owns the staging path.
"""

from __future__ import annotations

import errno
import logging
import os
import re
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Callable, Iterator

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
_ROOT_COORDINATION_LOCK_NAME = ".uv-root-staging-allocation.lock"
_ROOT_COORDINATION_PROCESS_LOCK = threading.RLock()
_PROCESS_LEASES_GUARD = threading.RLock()
_PROCESS_LEASES: dict[str, tuple[BinaryIO, Path]] = {}


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


def _acquire_os_lock(handle: BinaryIO) -> None:
    """Acquire one coordination lock, waiting only on another live runtime."""

    handle.seek(0)
    if os.name == "nt":
        while True:
            if _try_acquire_os_lock(handle):
                return
            time.sleep(0.1)

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


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


def _remove_lease_file(lease_path: Path) -> None:
    try:
        lease_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("could not remove UV root staging lease %s: %s", lease_path.name, exc)


@contextmanager
def _root_coordination_lock(root: Path) -> Iterator[None]:
    """Serialize lease publication and recovery across processes.

    The per-staging lease file must never become visible to startup recovery before
    its owner lock is established. A tiny permanent root coordination file closes
    that publication window without pre-creating producer output bytes. The lock is
    held only while allocating a lease or scanning stale leases, never during render
    or provider work, and OS ownership disappears automatically on process loss.
    """

    root = _validate_root(root)
    lock_path = root / _ROOT_COORDINATION_LOCK_NAME
    if lock_path.is_symlink():
        raise OSError("root staging coordination lock must not be a symlink")

    with _ROOT_COORDINATION_PROCESS_LOCK:
        handle = lock_path.open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            _acquire_os_lock(handle)
            try:
                yield
            finally:
                _release_os_lock(handle)
        finally:
            handle.close()


def _allocate_leased_path(root: Path, *, name_factory: Callable[[str], str]) -> Path:
    root = _validate_root(root)
    with _root_coordination_lock(root):
        for _ in range(16):
            token = uuid.uuid4().hex
            name = name_factory(token)
            if not _is_owned_staging_name(name):  # pragma: no cover - factory invariant
                raise ValueError(f"root staging factory produced an unowned name: {name!r}")
            staging_path = root / name
            lease_path = root / f"{name}{_LEASE_SUFFIX}"
            try:
                handle = lease_path.open("x+b")
            except FileExistsError:
                continue
            try:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
                if not _try_acquire_os_lock(handle):  # pragma: no cover - unique lease invariant
                    raise OSError("new root staging lease was unexpectedly already locked")
                if staging_path.exists() or staging_path.is_symlink():
                    _release_os_lock(handle)
                    handle.close()
                    _remove_lease_file(lease_path)
                    continue
                key = str(staging_path)
                with _PROCESS_LEASES_GUARD:
                    if key in _PROCESS_LEASES:  # pragma: no cover - UUID/name invariant
                        _release_os_lock(handle)
                        handle.close()
                        _remove_lease_file(lease_path)
                        continue
                    _PROCESS_LEASES[key] = (handle, lease_path)
                return staging_path
            except Exception:
                if not handle.closed:
                    try:
                        _release_os_lock(handle)
                    except Exception:
                        pass
                    handle.close()
                _remove_lease_file(lease_path)
                raise
    raise FileExistsError("could not allocate a unique UV root staging path")


def release_root_staging(staging_path: Path) -> None:
    """Release one path allocated by this process and remove any remaining bytes."""

    staging_path = Path(staging_path)
    key = str(staging_path)
    with _PROCESS_LEASES_GUARD:
        lease = _PROCESS_LEASES.pop(key, None)
    if lease is None:
        raise ValueError(f"root staging path is not leased by this process: {staging_path.name!r}")
    handle, lease_path = lease
    try:
        staging_path.unlink(missing_ok=True)
    finally:
        try:
            _release_os_lock(handle)
        finally:
            handle.close()
            _remove_lease_file(lease_path)


def acquire_generation_root_staging(root: Path, attempt_id: str, suffix: str) -> Path:
    attempt_id = _validate_identity(attempt_id, prefix="attempt_", field_name="attempt_id")
    suffix = _validate_suffix(suffix)
    return _allocate_leased_path(
        root,
        name_factory=lambda token: f".uv-generation-{attempt_id}-{token}{suffix}",
    )


def acquire_source_upload_root_staging(root: Path, source_id: str) -> Path:
    source_id = _validate_identity(source_id, prefix="src_", field_name="source_id")
    return _allocate_leased_path(
        root,
        name_factory=lambda token: f".uv-source-upload-{source_id}.{token}.upload",
    )


def acquire_webvtt_root_staging(root: Path, artifact_id: str) -> Path:
    artifact_id = _validate_identity(artifact_id, prefix="sub_", field_name="artifact_id")
    return _allocate_leased_path(
        root,
        name_factory=lambda token: f".uv-webvtt-{artifact_id}-{token}.vtt",
    )


def acquire_ffconcat_root_staging(root: Path) -> Path:
    return _allocate_leased_path(
        root,
        name_factory=lambda token: f".uv-ffconcat-{token}.txt",
    )


def acquire_timeline_root_staging(root: Path, artifact_id: str, suffix: str) -> Path:
    artifact_id = _validate_identity(artifact_id, prefix="art_", field_name="artifact_id")
    suffix = _validate_suffix(suffix)
    return _allocate_leased_path(
        root,
        name_factory=lambda token: f".uv-timeline-assemble-{artifact_id}-{token}{suffix}",
    )


@contextmanager
def generation_root_staging(root: Path, attempt_id: str, suffix: str) -> Iterator[Path]:
    path = acquire_generation_root_staging(root, attempt_id, suffix)
    try:
        yield path
    finally:
        release_root_staging(path)


@contextmanager
def source_upload_root_staging(root: Path, source_id: str) -> Iterator[Path]:
    path = acquire_source_upload_root_staging(root, source_id)
    try:
        yield path
    finally:
        release_root_staging(path)


@contextmanager
def webvtt_root_staging(root: Path, artifact_id: str) -> Iterator[Path]:
    path = acquire_webvtt_root_staging(root, artifact_id)
    try:
        yield path
    finally:
        release_root_staging(path)


@contextmanager
def ffconcat_root_staging(root: Path) -> Iterator[Path]:
    path = acquire_ffconcat_root_staging(root)
    try:
        yield path
    finally:
        release_root_staging(path)


@contextmanager
def timeline_root_staging(root: Path, artifact_id: str, suffix: str) -> Iterator[Path]:
    path = acquire_timeline_root_staging(root, artifact_id, suffix)
    try:
        yield path
    finally:
        release_root_staging(path)


def recover_stale_root_staging(root: Path) -> tuple[Path, ...]:
    """Remove exact UV staging files only after their lease proves no live owner.

    The scan is deliberately non-recursive. Unknown root files, project directories,
    symlinks, malformed or legacy unleased staging names, and currently locked leases
    are preserved. Legacy unleased names cannot be reclaimed safely while an older
    runtime may still be writing them; all staging allocated by this authority is
    lease-backed and therefore deterministically reclaimable after process loss.
    """

    root = _validate_root(root)
    recovered: list[Path] = []
    with _root_coordination_lock(root):
        entries = tuple(root.iterdir())
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
            acquired = False
            remove_lease = False
            try:
                try:
                    acquired = _try_acquire_os_lock(handle)
                except OSError as exc:
                    logger.error("could not inspect UV root staging lease %s: %s", lease_path.name, exc)
                    continue
                if not acquired:
                    continue
                staging_path = root / staging_name
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
                if acquired:
                    try:
                        _release_os_lock(handle)
                    except OSError as exc:
                        logger.warning("could not release UV root staging lease %s: %s", lease_path.name, exc)
                handle.close()
            if remove_lease:
                _remove_lease_file(lease_path)
    return tuple(recovered)
