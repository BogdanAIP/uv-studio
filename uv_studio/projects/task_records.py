"""Atomic versioned task/run records inside canonical UV Studio projects."""

from __future__ import annotations

import errno
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from .models import validate_identifier
from .store import ProjectStore


class ProjectTaskRecordConflict(RuntimeError):
    """A conditional task-record write observed a different durable snapshot."""


_PROCESS_LOCKS_GUARD = threading.RLock()
_PROCESS_LOCKS: dict[str, threading.RLock] = {}
_PROCESS_LOCK_CONTEXT = threading.local()


def _process_lock_for(path: Path) -> threading.RLock:
    key = str(path)
    with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PROCESS_LOCKS[key] = lock
        return lock


def _held_project_locks() -> dict[str, Any]:
    held = getattr(_PROCESS_LOCK_CONTEXT, "held", None)
    if held is None:
        held = {}
        _PROCESS_LOCK_CONTEXT.held = held
    return held


def _is_windows_lock_contention(exc: OSError) -> bool:
    return (
        exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK, errno.EPERM}
        or getattr(exc, "winerror", None) in {32, 33, 36}
    )


def _acquire_os_lock(handle: Any) -> None:
    if os.name == "nt":
        import msvcrt

        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError as exc:
                if not _is_windows_lock_contention(exc):
                    raise
                time.sleep(0.1)
    import fcntl

    handle.seek(0)
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _release_os_lock(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    handle.seek(0)
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class ProjectTaskRecordStore:
    """Write canonical JSON run records under the project's existing tasks/ root.

    Every project task-root mutation follows one lock order:

    ``ProjectStore._lock -> process RLock -> OS project lock -> record-store lock``.

    This keeps existing callers that already hold ``ProjectStore._lock`` compatible
    while preventing the inverse order that can deadlock a Stage-16 execution against
    plan/trace/job append paths. The OS lock is re-entrant across record-store
    instances on the same thread and is released automatically if the process exits.
    """

    LOCK_FILE_NAME = ".uv-task-records.lock"

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self._lock = threading.RLock()

    def path(self, project_id: str, run_id: str) -> Path:
        validate_identifier(run_id, field_name="run_id")
        return self.project_store.resolve_project_file(
            project_id,
            f"tasks/{run_id}.json",
            allowed_roots=("tasks",),
        )

    def _project_lock_path(self, project_id: str) -> Path:
        project_dir = self.project_store.project_directory(project_id)
        lexical_lock_path = project_dir / "tasks" / self.LOCK_FILE_NAME
        if lexical_lock_path.is_symlink():
            raise ProjectTaskRecordConflict("project lock path must not be a symlink")
        return self.project_store.resolve_project_file(
            project_id,
            f"tasks/{self.LOCK_FILE_NAME}",
            allowed_roots=("tasks",),
        )

    @contextmanager
    def project_lock(self, project_id: str) -> Iterator[None]:
        """Serialize task-root critical sections across threads and processes."""

        with self.project_store._lock:
            self.project_store.load_project(project_id)
            lock_path = self._project_lock_path(project_id)
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            key = str(lock_path)
            process_lock = _process_lock_for(lock_path)

            with process_lock:
                held = _held_project_locks()
                if key in held:
                    yield
                    return

                handle = lock_path.open("a+b")
                try:
                    handle.seek(0, os.SEEK_END)
                    if handle.tell() == 0:
                        handle.write(b"\0")
                        handle.flush()
                        os.fsync(handle.fileno())
                    _acquire_os_lock(handle)
                    held[key] = handle
                    try:
                        yield
                    finally:
                        held.pop(key, None)
                        _release_os_lock(handle)
                finally:
                    handle.close()

    @staticmethod
    def _serialize(data: Mapping[str, Any]) -> str:
        return json.dumps(
            dict(data),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"

    def _write_locked(self, path: Path, data: Mapping[str, Any]) -> Path:
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            serialized = self._serialize(data)
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except Exception:
            temp.unlink(missing_ok=True)
            raise
        return path

    def write(self, project_id: str, run_id: str, data: Mapping[str, Any]) -> Path:
        if not isinstance(data, Mapping):
            raise TypeError("task record must be a mapping")
        path = self.path(project_id, run_id)
        with self.project_lock(project_id), self._lock:
            return self._write_locked(path, data)

    def create_if_absent(
        self,
        project_id: str,
        run_id: str,
        data: Mapping[str, Any],
    ) -> Path:
        """Create one durable record iff no record/symlink already occupies its ID."""

        if not isinstance(data, Mapping):
            raise TypeError("task record must be a mapping")
        path = self.path(project_id, run_id)
        with self.project_lock(project_id), self._lock:
            if path.exists() or path.is_symlink():
                raise ProjectTaskRecordConflict(
                    f"task record already exists: {run_id!r}"
                )
            return self._write_locked(path, data)

    def compare_and_swap(
        self,
        project_id: str,
        run_id: str,
        *,
        expected: Mapping[str, Any],
        replacement: Mapping[str, Any],
    ) -> Path:
        """Replace one record iff its durable JSON still equals ``expected``."""

        if not isinstance(expected, Mapping) or not isinstance(replacement, Mapping):
            raise TypeError("conditional task record values must be mappings")
        path = self.path(project_id, run_id)
        with self.project_lock(project_id), self._lock:
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError as exc:
                raise ProjectTaskRecordConflict(
                    f"task record disappeared before conditional write: {run_id!r}"
                ) from exc
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise ProjectTaskRecordConflict(
                    f"task record could not be verified before conditional write: {run_id!r}"
                ) from exc
            if not isinstance(current, Mapping) or dict(current) != dict(expected):
                raise ProjectTaskRecordConflict(
                    f"task record changed before conditional write: {run_id!r}"
                )
            return self._write_locked(path, replacement)
