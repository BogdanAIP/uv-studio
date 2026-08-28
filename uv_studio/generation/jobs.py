"""Project-scoped durable generation jobs and execution-attempt history."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from uv_studio.projects.models import (
    ProjectValidationError,
    utc_now_iso,
    validate_identifier,
)
from uv_studio.projects.store import ProjectStore, ProjectStoreError
from uv_studio.projects.task_records import ProjectTaskRecordStore

from .models import GenerationContract, GenerationValidationError

GENERATION_JOB_SCHEMA_VERSION = 1
GENERATION_JOB_RECORD_TYPE = "generation_job"


class GenerationJobError(RuntimeError):
    pass


class GenerationJobConflict(GenerationJobError):
    pass


class GenerationJobNotFound(GenerationJobError):
    pass


class GenerationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _status(value: Any, *, field_name: str) -> GenerationStatus:
    if isinstance(value, GenerationStatus):
        return value
    try:
        return GenerationStatus(value)
    except (TypeError, ValueError) as exc:
        raise GenerationJobError(f"invalid {field_name}: {value!r}") from exc


def _portable_json(value: Any, *, field_name: str) -> Any:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise GenerationValidationError(f"{field_name} must contain portable JSON") from exc


def _bounded_error(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GenerationJobError("attempt error must be non-empty text when present")
    return value.strip()[:4000]


def generation_request_digest(
    *,
    project_id: str,
    shot_id: str,
    model_id: str,
    capability_id: str,
    offer_id: str,
    adapter_id: str,
    inputs: Mapping[str, Any],
    contract: GenerationContract,
) -> tuple[str, dict[str, Any]]:
    """Return stable SHA-256 and detached normalized request content."""

    try:
        validate_identifier(project_id, field_name="project_id")
        validate_identifier(shot_id, field_name="shot_id")
    except ProjectValidationError as exc:
        raise GenerationValidationError(str(exc)) from exc
    if not isinstance(inputs, Mapping):
        raise GenerationValidationError("generation inputs must be a JSON object")
    if not isinstance(contract, GenerationContract):
        raise GenerationValidationError("contract must be a GenerationContract")
    normalized = _portable_json(
        {
            "project_id": project_id,
            "shot_id": shot_id,
            "model_id": model_id,
            "execution_mapping": {
                "capability_id": capability_id,
                "offer_id": offer_id,
                "adapter_id": adapter_id,
            },
            "inputs": dict(inputs),
            "generation_contract": contract.to_dict(),
        },
        field_name="generation request",
    )
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), normalized


@dataclass(frozen=True)
class GenerationExecutionAttempt:
    attempt_id: str
    retry_index: int
    status: GenerationStatus
    started_at: str
    ended_at: str | None = None
    output_reference_id: str | None = None
    take_id: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "attempt_id",
                validate_identifier(self.attempt_id, field_name="attempt_id"),
            )
        except ProjectValidationError as exc:
            raise GenerationJobError(str(exc)) from exc
        if isinstance(self.retry_index, bool) or not isinstance(self.retry_index, int) or self.retry_index < 0:
            raise GenerationJobError("retry_index must be an integer >= 0")
        object.__setattr__(self, "status", _status(self.status, field_name="attempt status"))
        if self.status not in {
            GenerationStatus.RUNNING,
            GenerationStatus.SUCCEEDED,
            GenerationStatus.FAILED,
            GenerationStatus.CANCELLED,
        }:
            raise GenerationJobError("execution attempt cannot be queued")
        if not isinstance(self.started_at, str) or not self.started_at:
            raise GenerationJobError("attempt started_at is required")
        if self.ended_at is not None and (not isinstance(self.ended_at, str) or not self.ended_at):
            raise GenerationJobError("attempt ended_at must be non-empty text when present")
        for field_name in ("output_reference_id", "take_id"):
            value = getattr(self, field_name)
            if value is not None:
                try:
                    validate_identifier(value, field_name=field_name)
                except ProjectValidationError as exc:
                    raise GenerationJobError(str(exc)) from exc
        object.__setattr__(self, "error", _bounded_error(self.error))
        if self.status is GenerationStatus.SUCCEEDED:
            if self.ended_at is None or self.output_reference_id is None or self.take_id is None:
                raise GenerationJobError("succeeded attempt requires end time, output reference and take")
            if self.error is not None:
                raise GenerationJobError("succeeded attempt must not contain error")
        elif self.status in {GenerationStatus.FAILED, GenerationStatus.CANCELLED}:
            if self.ended_at is None:
                raise GenerationJobError("terminal attempt requires ended_at")
        elif self.ended_at is not None:
            raise GenerationJobError("running attempt must not have ended_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "retry_index": self.retry_index,
            "status": self.status.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "output_reference_id": self.output_reference_id,
            "take_id": self.take_id,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GenerationExecutionAttempt":
        if not isinstance(data, Mapping):
            raise GenerationJobError("generation attempt must be a JSON object")
        try:
            return cls(
                attempt_id=data["attempt_id"],
                retry_index=data["retry_index"],
                status=data["status"],
                started_at=data["started_at"],
                ended_at=data.get("ended_at"),
                output_reference_id=data.get("output_reference_id"),
                take_id=data.get("take_id"),
                error=data.get("error"),
            )
        except KeyError as exc:
            raise GenerationJobError(f"missing generation attempt field: {exc.args[0]}") from exc


@dataclass(frozen=True)
class GenerationJob:
    job_id: str
    project_id: str
    idempotency_key: str
    request_digest: str
    request: dict[str, Any]
    status: GenerationStatus
    created_at: str
    updated_at: str
    attempts: tuple[GenerationExecutionAttempt, ...] = ()
    schema_version: int = GENERATION_JOB_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GENERATION_JOB_SCHEMA_VERSION:
            raise GenerationJobError(
                f"GenerationJob only represents schema v{GENERATION_JOB_SCHEMA_VERSION}"
            )
        try:
            object.__setattr__(self, "job_id", validate_identifier(self.job_id, field_name="job_id"))
            object.__setattr__(
                self,
                "project_id",
                validate_identifier(self.project_id, field_name="project_id"),
            )
            object.__setattr__(
                self,
                "idempotency_key",
                validate_identifier(self.idempotency_key, field_name="idempotency_key"),
            )
        except ProjectValidationError as exc:
            raise GenerationJobError(str(exc)) from exc
        if (
            not isinstance(self.request_digest, str)
            or len(self.request_digest) != 64
            or any(ch not in "0123456789abcdef" for ch in self.request_digest)
        ):
            raise GenerationJobError("request_digest must be lowercase SHA-256 hex")
        if not isinstance(self.request, Mapping):
            raise GenerationJobError("generation job request must be a JSON object")
        object.__setattr__(self, "request", _portable_json(dict(self.request), field_name="job request"))
        object.__setattr__(self, "status", _status(self.status, field_name="job status"))
        if not isinstance(self.created_at, str) or not self.created_at:
            raise GenerationJobError("job created_at is required")
        if not isinstance(self.updated_at, str) or not self.updated_at:
            raise GenerationJobError("job updated_at is required")
        attempts = tuple(self.attempts)
        if any(not isinstance(item, GenerationExecutionAttempt) for item in attempts):
            raise GenerationJobError("job attempts must contain GenerationExecutionAttempt values")
        if len({item.attempt_id for item in attempts}) != len(attempts):
            raise GenerationJobError("job attempt ids must be unique")
        if tuple(item.retry_index for item in attempts) != tuple(range(len(attempts))):
            raise GenerationJobError("job retry indexes must be contiguous from zero")
        object.__setattr__(self, "attempts", attempts)
        running = [item for item in attempts if item.status is GenerationStatus.RUNNING]
        if len(running) > 1:
            raise GenerationJobError("job cannot contain multiple running attempts")
        if self.status is GenerationStatus.QUEUED and running:
            raise GenerationJobError("queued job cannot contain a running attempt")
        if self.status is GenerationStatus.RUNNING:
            if not attempts or attempts[-1].status is not GenerationStatus.RUNNING:
                raise GenerationJobError("running job must end with a running attempt")
        if self.status is GenerationStatus.SUCCEEDED:
            if not attempts or attempts[-1].status is not GenerationStatus.SUCCEEDED:
                raise GenerationJobError("succeeded job must end with a succeeded attempt")
        if self.status is GenerationStatus.FAILED:
            if not attempts or attempts[-1].status is not GenerationStatus.FAILED:
                raise GenerationJobError("failed job must end with a failed attempt")

    @property
    def current_attempt(self) -> GenerationExecutionAttempt | None:
        return self.attempts[-1] if self.attempts else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": GENERATION_JOB_RECORD_TYPE,
            "schema_version": self.schema_version,
            "job_id": self.job_id,
            "project_id": self.project_id,
            "idempotency_key": self.idempotency_key,
            "request_digest": self.request_digest,
            "request": dict(self.request),
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "attempts": [item.to_dict() for item in self.attempts],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GenerationJob":
        if not isinstance(data, Mapping) or data.get("record_type") != GENERATION_JOB_RECORD_TYPE:
            raise GenerationJobError("task record is not a generation job")
        try:
            return cls(
                schema_version=data["schema_version"],
                job_id=data["job_id"],
                project_id=data["project_id"],
                idempotency_key=data["idempotency_key"],
                request_digest=data["request_digest"],
                request=dict(data["request"]),
                status=data["status"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                attempts=tuple(
                    GenerationExecutionAttempt.from_dict(item)
                    for item in data.get("attempts", [])
                ),
            )
        except KeyError as exc:
            raise GenerationJobError(f"missing generation job field: {exc.args[0]}") from exc


class GenerationJobManager:
    """Durable Job authority; semantic acceptance remains outside this history."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)

    def create_or_reuse(
        self,
        *,
        project_id: str,
        idempotency_key: str,
        request_digest: str,
        request: Mapping[str, Any],
    ) -> tuple[GenerationJob, bool]:
        """Reserve one creative Job. Returns ``(job, reused)``."""

        with self.records.project_lock(project_id):
            self.project_store.load_project(project_id)
            try:
                validate_identifier(idempotency_key, field_name="idempotency_key")
            except ProjectValidationError as exc:
                raise GenerationValidationError(str(exc)) from exc
            for job in self._list_unlocked(project_id):
                if job.idempotency_key != idempotency_key:
                    continue
                if job.request_digest != request_digest:
                    raise GenerationJobConflict(
                        "idempotency key is already bound to a different generation request"
                    )
                return job, True
            now = utc_now_iso()
            job = GenerationJob(
                job_id=f"job_{uuid.uuid4().hex}",
                project_id=project_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                request=dict(request),
                status=GenerationStatus.QUEUED,
                created_at=now,
                updated_at=now,
            )
            self._write_unlocked(job)
            return job, False

    def get(self, project_id: str, job_id: str) -> GenerationJob:
        with self.project_store._lock:
            self.project_store.load_project(project_id)
            return self._read_unlocked(project_id, job_id)

    def list(self, project_id: str) -> tuple[GenerationJob, ...]:
        with self.project_store._lock:
            self.project_store.load_project(project_id)
            return tuple(self._list_unlocked(project_id))

    def start_execution(self, project_id: str, job_id: str) -> GenerationJob:
        """Start initial execution or an explicit infrastructure retry after failure."""

        with self.project_store._lock:
            job = self._read_unlocked(project_id, job_id)
            if job.status not in {GenerationStatus.QUEUED, GenerationStatus.FAILED}:
                raise GenerationJobConflict(
                    f"job {job.job_id!r} cannot start from status {job.status.value!r}"
                )
            attempt = GenerationExecutionAttempt(
                attempt_id=f"attempt_{uuid.uuid4().hex}",
                retry_index=len(job.attempts),
                status=GenerationStatus.RUNNING,
                started_at=utc_now_iso(),
            )
            updated = replace(
                job,
                status=GenerationStatus.RUNNING,
                updated_at=utc_now_iso(),
                attempts=(*job.attempts, attempt),
            )
            self._write_unlocked(updated)
            return updated

    def succeed(
        self,
        project_id: str,
        job_id: str,
        *,
        attempt_id: str,
        output_reference_id: str,
        take_id: str,
    ) -> GenerationJob:
        with self.project_store._lock:
            job = self._read_unlocked(project_id, job_id)
            attempt = self._require_running_attempt(job, attempt_id)
            completed = replace(
                attempt,
                status=GenerationStatus.SUCCEEDED,
                ended_at=utc_now_iso(),
                output_reference_id=output_reference_id,
                take_id=take_id,
                error=None,
            )
            updated = replace(
                job,
                status=GenerationStatus.SUCCEEDED,
                updated_at=completed.ended_at,
                attempts=(*job.attempts[:-1], completed),
            )
            self._write_unlocked(updated)
            return updated

    def fail(
        self,
        project_id: str,
        job_id: str,
        *,
        attempt_id: str,
        error: str,
    ) -> GenerationJob:
        with self.project_store._lock:
            job = self._read_unlocked(project_id, job_id)
            attempt = self._require_running_attempt(job, attempt_id)
            completed = replace(
                attempt,
                status=GenerationStatus.FAILED,
                ended_at=utc_now_iso(),
                error=error,
            )
            updated = replace(
                job,
                status=GenerationStatus.FAILED,
                updated_at=completed.ended_at,
                attempts=(*job.attempts[:-1], completed),
            )
            self._write_unlocked(updated)
            return updated

    def cancel(self, project_id: str, job_id: str) -> GenerationJob:
        with self.project_store._lock:
            job = self._read_unlocked(project_id, job_id)
            if job.status is GenerationStatus.QUEUED:
                updated = replace(
                    job,
                    status=GenerationStatus.CANCELLED,
                    updated_at=utc_now_iso(),
                )
            elif job.status is GenerationStatus.RUNNING:
                attempt = job.current_attempt
                if attempt is None:  # pragma: no cover - dataclass invariant
                    raise GenerationJobError("running job lost its current attempt")
                ended_at = utc_now_iso()
                cancelled = replace(
                    attempt,
                    status=GenerationStatus.CANCELLED,
                    ended_at=ended_at,
                    error="cancelled",
                )
                updated = replace(
                    job,
                    status=GenerationStatus.CANCELLED,
                    updated_at=ended_at,
                    attempts=(*job.attempts[:-1], cancelled),
                )
            else:
                raise GenerationJobConflict(
                    f"job {job.job_id!r} cannot be cancelled from status {job.status.value!r}"
                )
            self._write_unlocked(updated)
            return updated

    @staticmethod
    def _require_running_attempt(
        job: GenerationJob,
        attempt_id: str,
    ) -> GenerationExecutionAttempt:
        attempt = job.current_attempt
        if (
            job.status is not GenerationStatus.RUNNING
            or attempt is None
            or attempt.status is not GenerationStatus.RUNNING
            or attempt.attempt_id != attempt_id
        ):
            raise GenerationJobConflict("job does not have the requested running attempt")
        return attempt

    def _record_path(self, project_id: str, job_id: str) -> Path:
        return self.records.path(project_id, job_id)

    def _read_unlocked(self, project_id: str, job_id: str) -> GenerationJob:
        try:
            validate_identifier(job_id, field_name="job_id")
        except ProjectValidationError as exc:
            raise GenerationJobNotFound(job_id) from exc
        path = self._record_path(project_id, job_id)
        if not path.is_file():
            raise GenerationJobNotFound(job_id)
        try:
            raw = json.loads(
                path.read_text(encoding="utf-8"),
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-finite JSON number {value!r}")
                ),
            )
            job = GenerationJob.from_dict(raw)
        except (OSError, ValueError, json.JSONDecodeError, GenerationJobError) as exc:
            raise GenerationJobError(f"invalid generation job record {path.name!r}: {exc}") from exc
        if job.project_id != project_id or job.job_id != job_id:
            raise GenerationJobError("generation job record identity mismatch")
        return job

    def _list_unlocked(self, project_id: str) -> list[GenerationJob]:
        tasks = self.project_store.project_directory(project_id) / "tasks"
        jobs: list[GenerationJob] = []
        for path in sorted(tasks.glob("job_*.json"), key=lambda item: item.name):
            if path.is_symlink() or not path.is_file():
                continue
            job_id = path.stem
            jobs.append(self._read_unlocked(project_id, job_id))
        jobs.sort(key=lambda item: (item.created_at, item.job_id))
        return jobs

    def _write_unlocked(self, job: GenerationJob) -> None:
        try:
            self.records.write(job.project_id, job.job_id, job.to_dict())
        except (OSError, ProjectStoreError, ProjectValidationError, TypeError, ValueError) as exc:
            raise GenerationJobError(f"could not persist generation job {job.job_id!r}: {exc}") from exc
