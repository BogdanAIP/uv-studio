"""Process-local capability execution jobs with fail-closed cancellation state."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock, Thread
from typing import Any, Callable

from .execution import CapabilityExecutionCancelled, CapabilityExecutionError
from .process_control import CancellationToken

CAPABILITY_JOB_SCHEMA_VERSION = 1


class CapabilityJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATUSES = {
    CapabilityJobStatus.SUCCEEDED,
    CapabilityJobStatus.FAILED,
    CapabilityJobStatus.CANCELLED,
}


class CapabilityJobStoreError(RuntimeError):
    pass


class CapabilityJobNotFound(CapabilityJobStoreError):
    pass


class CapabilityJobCapacityExceeded(CapabilityJobStoreError):
    pass


JobExecutor = Callable[[CancellationToken], dict[str, Any]]


@dataclass
class _CapabilityJobRecord:
    job_id: str
    project_id: str
    capability_id: str
    offer_id: str
    adapter_id: str
    cancellation: CancellationToken = field(default_factory=CancellationToken)
    status: CapabilityJobStatus = CapabilityJobStatus.QUEUED
    created_at_unix: float = field(default_factory=time.time)
    started_at_unix: float | None = None
    finished_at_unix: float | None = None
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    thread: Thread | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CAPABILITY_JOB_SCHEMA_VERSION,
            "job_id": self.job_id,
            "project_id": self.project_id,
            "capability_id": self.capability_id,
            "offer_id": self.offer_id,
            "adapter_id": self.adapter_id,
            "status": self.status.value,
            "cancel_requested": self.cancellation.is_cancelled,
            "created_at_unix": self.created_at_unix,
            "started_at_unix": self.started_at_unix,
            "finished_at_unix": self.finished_at_unix,
            "result": None if self.result is None else dict(self.result),
            "error": None if self.error is None else dict(self.error),
        }


class CapabilityExecutionJobStore:
    """Bounded in-memory job registry for one running UV Studio backend process.

    Job records intentionally do not persist request input or authorization tokens.
    Canonical project changes remain owned by the selected capability adapter.
    """

    def __init__(self, *, max_jobs: int = 128) -> None:
        if max_jobs <= 0:
            raise ValueError("max_jobs must be positive")
        self.max_jobs = max_jobs
        self._jobs: dict[str, _CapabilityJobRecord] = {}
        self._lock = RLock()

    def _prune_terminal_locked(self) -> None:
        if len(self._jobs) < self.max_jobs:
            return
        terminal = sorted(
            (
                record
                for record in self._jobs.values()
                if record.status in _TERMINAL_STATUSES
            ),
            key=lambda item: (
                item.finished_at_unix if item.finished_at_unix is not None else item.created_at_unix,
                item.created_at_unix,
            ),
        )
        while len(self._jobs) >= self.max_jobs and terminal:
            record = terminal.pop(0)
            self._jobs.pop(record.job_id, None)

    def create(
        self,
        *,
        project_id: str,
        capability_id: str,
        offer_id: str,
        adapter_id: str,
        executor: JobExecutor,
    ) -> dict[str, Any]:
        with self._lock:
            self._prune_terminal_locked()
            if len(self._jobs) >= self.max_jobs:
                raise CapabilityJobCapacityExceeded(
                    "too many capability jobs are active; wait for a job to finish before starting another"
                )
            record = _CapabilityJobRecord(
                job_id=f"job_{uuid.uuid4().hex}",
                project_id=project_id,
                capability_id=capability_id,
                offer_id=offer_id,
                adapter_id=adapter_id,
            )
            thread = Thread(
                target=self._run_job,
                args=(record.job_id, executor),
                name=f"uv-capability-{record.job_id[-12:]}",
                daemon=True,
            )
            record.thread = thread
            self._jobs[record.job_id] = record
            snapshot = record.to_dict()
            thread.start()
            return snapshot

    def _run_job(self, job_id: str, executor: JobExecutor) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            if record.status is CapabilityJobStatus.CANCELLED:
                return
            record.status = CapabilityJobStatus.RUNNING
            record.started_at_unix = time.time()

        try:
            result = executor(record.cancellation)
        except CapabilityExecutionCancelled:
            with self._lock:
                current = self._jobs.get(job_id)
                if current is not None:
                    current.status = CapabilityJobStatus.CANCELLED
                    current.finished_at_unix = time.time()
                    current.result = None
                    current.error = None
            return
        except CapabilityExecutionError as exc:
            with self._lock:
                current = self._jobs.get(job_id)
                if current is not None:
                    current.status = CapabilityJobStatus.FAILED
                    current.finished_at_unix = time.time()
                    current.result = None
                    current.error = {
                        "code": getattr(exc, "code", "capability_execution_failed"),
                        "message": str(exc),
                    }
            return
        except Exception:
            with self._lock:
                current = self._jobs.get(job_id)
                if current is not None:
                    current.status = CapabilityJobStatus.FAILED
                    current.finished_at_unix = time.time()
                    current.result = None
                    current.error = {
                        "code": "capability_job_internal_error",
                        "message": "capability execution failed unexpectedly",
                    }
            return

        with self._lock:
            current = self._jobs.get(job_id)
            if current is None:
                return
            current.status = CapabilityJobStatus.SUCCEEDED
            current.finished_at_unix = time.time()
            current.result = dict(result)
            current.error = None

    def _record_for_project(self, project_id: str, job_id: str) -> _CapabilityJobRecord:
        record = self._jobs.get(job_id)
        if record is None or record.project_id != project_id:
            raise CapabilityJobNotFound("capability job not found")
        return record

    def get(self, *, project_id: str, job_id: str) -> dict[str, Any]:
        with self._lock:
            return self._record_for_project(project_id, job_id).to_dict()

    def cancel(self, *, project_id: str, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._record_for_project(project_id, job_id)
            if record.status in _TERMINAL_STATUSES:
                return record.to_dict()
            record.cancellation.cancel()
            if record.status is CapabilityJobStatus.QUEUED:
                record.status = CapabilityJobStatus.CANCELLED
                record.finished_at_unix = time.time()
            elif record.status is CapabilityJobStatus.RUNNING:
                record.status = CapabilityJobStatus.CANCELLING
            return record.to_dict()

    def wait_for_terminal(
        self,
        *,
        project_id: str,
        job_id: str,
        timeout_sec: float = 5.0,
        poll_interval_sec: float = 0.01,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_sec
        while True:
            snapshot = self.get(project_id=project_id, job_id=job_id)
            if snapshot["status"] in {item.value for item in _TERMINAL_STATUSES}:
                return snapshot
            if time.monotonic() >= deadline:
                raise TimeoutError(f"capability job {job_id} did not reach a terminal state")
            time.sleep(poll_interval_sec)
