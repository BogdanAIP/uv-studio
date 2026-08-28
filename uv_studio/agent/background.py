"""D-066 layer 4: bounded background Agent execution over existing authorities.

This module deliberately does not introduce another scheduler or task graph.  It
adds worker ownership beside the existing durable AgentTaskRecord state and reuses
the Stage-16/17 policy, trace, transaction, Generation Job and recovery contracts.

The critical safety property is fencing: a worker lease is checked again at the
canonical commit boundary.  A worker that lost/expired ownership may continue
running Python code, but it cannot commit Production/Timeline state or submit a
Generation Job through the Agent path.
"""

from __future__ import annotations

import json
import threading
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterator, Mapping, Sequence

from uv_studio.projects.models import (
    ProjectValidationError,
    validate_identifier,
    validate_timestamp,
)
from uv_studio.projects.task_records import (
    ProjectTaskRecordConflict,
    ProjectTaskRecordStore,
)

from .models import AgentPolicyProjection, AgentTraceStatus, safe_error_message, stable_digest
from .orchestration import (
    AgentPlanRecord,
    AgentTaskBlocked,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_execution_evidence import _FinalCorrelatedProjectUnitOfWork
from .stage16_recovery import _execution_context, _execution_correlation
from .stage16_runtime import _typed_correlation_reference
from .stage17_provenance import AgentSubagentTaskCoordinator as _Stage17TaskCoordinator


AGENT_BACKGROUND_LEASE_SCHEMA_VERSION = 1
AGENT_BACKGROUND_LEASE_RECORD_TYPE = "agent_background_lease"
MAX_BACKGROUND_CLAIMS_PER_TASK = 8
MAX_BACKGROUND_LEASE_HISTORY = 8
MAX_BACKGROUND_LEASE_SECONDS = 300.0
MIN_BACKGROUND_LEASE_SECONDS = 1.0
MAX_BACKGROUND_TASK_BUDGET = 32

Clock = Callable[[], datetime]


class AgentBackgroundError(AgentTaskStateError):
    """Background execution state is invalid or unsafe to continue."""


class AgentBackgroundLeaseConflict(AgentBackgroundError):
    """Another live worker owns the Agent Task."""


class AgentBackgroundLeaseStale(AgentBackgroundError):
    """The caller no longer owns a live lease for the Agent Task."""


class AgentBackgroundContextStale(AgentBackgroundError):
    """Canonical Agent context changed after the background claim."""


class AgentBackgroundRetryLimit(AgentBackgroundError):
    """A bounded pre-dispatch claim retry budget was exhausted."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_now(clock: Clock) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise AgentBackgroundError("background clock must return timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, field_name: str) -> datetime:
    try:
        text = validate_timestamp(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise AgentBackgroundError(str(exc)) from exc
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    return datetime.fromisoformat(candidate).astimezone(timezone.utc)


def _digest(value: Any, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AgentBackgroundError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _lease_seconds(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentBackgroundError("lease_seconds must be numeric")
    normalized = float(value)
    if not MIN_BACKGROUND_LEASE_SECONDS <= normalized <= MAX_BACKGROUND_LEASE_SECONDS:
        raise AgentBackgroundError(
            "lease_seconds must be between "
            f"{MIN_BACKGROUND_LEASE_SECONDS:g} and {MAX_BACKGROUND_LEASE_SECONDS:g}"
        )
    return normalized


def _lease_record_id(plan_id: str, task_id: str) -> str:
    digest = stable_digest(
        {
            "record_type": AGENT_BACKGROUND_LEASE_RECORD_TYPE,
            "plan_id": plan_id,
            "task_id": task_id,
        }
    )
    return f"agent_bg_lease_{digest[:32]}"


def _history_entry(record: "AgentBackgroundLeaseRecord", *, outcome: str) -> dict[str, Any]:
    return {
        "generation": record.generation,
        "owner_id": record.owner_id,
        "token_digest": stable_digest({"lease_token": record.lease_token}),
        "acquired_at": record.acquired_at,
        "heartbeat_at": record.heartbeat_at,
        "expires_at": record.expires_at,
        "released_at": record.released_at,
        "outcome": outcome,
    }


@dataclass(frozen=True)
class AgentBackgroundLeaseRecord:
    """One mutable fencing lease stored under the existing project tasks authority."""

    record_id: str
    project_id: str
    plan_id: str
    task_id: str
    task_record_id: str
    generation: int
    owner_id: str
    lease_token: str
    acquired_at: str
    heartbeat_at: str
    expires_at: str
    context_digest: str
    input_digest: str
    target_shot_id: str | None
    released_at: str | None = None
    outcome: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    history: tuple[dict[str, Any], ...] = ()
    schema_version: int = AGENT_BACKGROUND_LEASE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_BACKGROUND_LEASE_SCHEMA_VERSION:
            raise AgentBackgroundError(
                f"background lease only represents schema v{AGENT_BACKGROUND_LEASE_SCHEMA_VERSION}"
            )
        for field_name in (
            "record_id",
            "project_id",
            "plan_id",
            "task_id",
            "task_record_id",
            "owner_id",
            "lease_token",
        ):
            try:
                object.__setattr__(
                    self,
                    field_name,
                    validate_identifier(getattr(self, field_name), field_name=field_name),
                )
            except ProjectValidationError as exc:
                raise AgentBackgroundError(str(exc)) from exc
        if self.record_id != _lease_record_id(self.plan_id, self.task_id):
            raise AgentBackgroundError("background lease record_id does not match plan/task identity")
        if isinstance(self.generation, bool) or not isinstance(self.generation, int):
            raise AgentBackgroundError("background lease generation must be an integer")
        if not 1 <= self.generation <= MAX_BACKGROUND_CLAIMS_PER_TASK:
            raise AgentBackgroundError("background lease generation exceeds bounded claim budget")

        acquired = _parse_time(self.acquired_at, field_name="lease acquired_at")
        heartbeat = _parse_time(self.heartbeat_at, field_name="lease heartbeat_at")
        expires = _parse_time(self.expires_at, field_name="lease expires_at")
        if heartbeat < acquired or expires <= heartbeat:
            raise AgentBackgroundError("background lease timestamps are not monotonic")
        if self.released_at is not None:
            released = _parse_time(self.released_at, field_name="lease released_at")
            if released < acquired:
                raise AgentBackgroundError("background lease released_at predates acquisition")
            if not isinstance(self.outcome, str) or not self.outcome.strip():
                raise AgentBackgroundError("released background lease requires an outcome")
        elif self.outcome is not None:
            raise AgentBackgroundError("active background lease cannot contain an outcome")

        if self.target_shot_id is not None:
            try:
                object.__setattr__(
                    self,
                    "target_shot_id",
                    validate_identifier(self.target_shot_id, field_name="target_shot_id"),
                )
            except ProjectValidationError as exc:
                raise AgentBackgroundError(str(exc)) from exc
        object.__setattr__(self, "context_digest", _digest(self.context_digest, field_name="context_digest"))
        object.__setattr__(self, "input_digest", _digest(self.input_digest, field_name="input_digest"))

        history = tuple(dict(item) for item in self.history)
        if len(history) > MAX_BACKGROUND_LEASE_HISTORY:
            raise AgentBackgroundError("background lease history exceeds bounded limit")
        object.__setattr__(self, "history", history)

    @property
    def active(self) -> bool:
        return self.released_at is None

    def is_expired(self, now: datetime) -> bool:
        return now >= _parse_time(self.expires_at, field_name="lease expires_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": AGENT_BACKGROUND_LEASE_RECORD_TYPE,
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "project_id": self.project_id,
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "task_record_id": self.task_record_id,
            "generation": self.generation,
            "owner_id": self.owner_id,
            "lease_token": self.lease_token,
            "acquired_at": self.acquired_at,
            "heartbeat_at": self.heartbeat_at,
            "expires_at": self.expires_at,
            "context_digest": self.context_digest,
            "input_digest": self.input_digest,
            "target_shot_id": self.target_shot_id,
            "released_at": self.released_at,
            "outcome": self.outcome,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "history": [dict(item) for item in self.history],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentBackgroundLeaseRecord":
        if not isinstance(data, Mapping) or data.get("record_type") != AGENT_BACKGROUND_LEASE_RECORD_TYPE:
            raise AgentBackgroundError("task record is not a background Agent lease")
        try:
            return cls(
                schema_version=data["schema_version"],
                record_id=data["record_id"],
                project_id=data["project_id"],
                plan_id=data["plan_id"],
                task_id=data["task_id"],
                task_record_id=data["task_record_id"],
                generation=data["generation"],
                owner_id=data["owner_id"],
                lease_token=data["lease_token"],
                acquired_at=data["acquired_at"],
                heartbeat_at=data["heartbeat_at"],
                expires_at=data["expires_at"],
                context_digest=data["context_digest"],
                input_digest=data["input_digest"],
                target_shot_id=data.get("target_shot_id"),
                released_at=data.get("released_at"),
                outcome=data.get("outcome"),
                error_type=data.get("error_type"),
                error_message=data.get("error_message"),
                history=tuple(data.get("history", ())),
            )
        except KeyError as exc:
            raise AgentBackgroundError(f"missing background lease field: {exc.args[0]}") from exc


class AgentBackgroundLeaseStore:
    """Durable worker ownership beside AgentTaskRecord, using the same task-root CAS."""

    def __init__(self, project_store: Any, *, clock: Clock = _utc_now) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)
        self.clock = clock

    def _load_locked(self, project_id: str, plan_id: str, task_id: str) -> AgentBackgroundLeaseRecord | None:
        record_id = _lease_record_id(plan_id, task_id)
        path = self.records.path(project_id, record_id)
        if not path.exists():
            return None
        if path.is_symlink() or not path.is_file():
            raise AgentBackgroundError("background lease path is not a regular file")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise AgentBackgroundError(f"could not read background lease: {exc}") from exc
        record = AgentBackgroundLeaseRecord.from_dict(raw)
        if (
            record.project_id != project_id
            or record.plan_id != plan_id
            or record.task_id != task_id
        ):
            raise AgentBackgroundError("background lease identity mismatch")
        return record

    def get(self, project_id: str, plan_id: str, task_id: str) -> AgentBackgroundLeaseRecord | None:
        with self.project_store._lock, self.records.project_lock(project_id):
            return self._load_locked(project_id, plan_id, task_id)

    def claim(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        task_record_id: str,
        owner_id: str,
        context_digest: str,
        input_digest: str,
        target_shot_id: str | None,
        lease_seconds: float,
    ) -> AgentBackgroundLeaseRecord:
        try:
            normalized_owner = validate_identifier(owner_id, field_name="worker_id")
        except ProjectValidationError as exc:
            raise AgentBackgroundError(str(exc)) from exc
        duration = _lease_seconds(lease_seconds)
        now = _normalized_now(self.clock)
        expires = now + timedelta(seconds=duration)

        with self.project_store._lock, self.records.project_lock(project_id):
            previous = self._load_locked(project_id, plan_id, task_id)
            history: list[dict[str, Any]] = []
            generation = 1
            if previous is not None:
                if previous.active and not previous.is_expired(now):
                    raise AgentBackgroundLeaseConflict(
                        f"Agent Task {task_id!r} is leased by worker {previous.owner_id!r}"
                    )
                if previous.generation >= MAX_BACKGROUND_CLAIMS_PER_TASK:
                    raise AgentBackgroundRetryLimit(
                        f"Agent Task {task_id!r} exhausted {MAX_BACKGROUND_CLAIMS_PER_TASK} claim attempts"
                    )
                generation = previous.generation + 1
                history.extend(previous.history)
                history.append(
                    _history_entry(
                        previous,
                        outcome=(
                            previous.outcome
                            if previous.released_at is not None and previous.outcome
                            else "lease_expired_before_dispatch"
                        ),
                    )
                )
                history = history[-MAX_BACKGROUND_LEASE_HISTORY:]

            record = AgentBackgroundLeaseRecord(
                record_id=_lease_record_id(plan_id, task_id),
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
                task_record_id=task_record_id,
                generation=generation,
                owner_id=normalized_owner,
                lease_token=f"agent_bg_token_{uuid.uuid4().hex}",
                acquired_at=_iso(now),
                heartbeat_at=_iso(now),
                expires_at=_iso(expires),
                context_digest=context_digest,
                input_digest=input_digest,
                target_shot_id=target_shot_id,
                history=tuple(history),
            )
            try:
                if previous is None:
                    self.records.create_if_absent(project_id, record.record_id, record.to_dict())
                else:
                    self.records.compare_and_swap(
                        project_id,
                        record.record_id,
                        expected=previous.to_dict(),
                        replacement=record.to_dict(),
                    )
            except ProjectTaskRecordConflict as exc:
                raise AgentBackgroundLeaseConflict(
                    f"Agent Task {task_id!r} lease changed during claim"
                ) from exc
            return record

    @staticmethod
    def _same_owner(current: AgentBackgroundLeaseRecord, claim: "AgentBackgroundClaim") -> bool:
        return (
            current.record_id == claim.lease_record_id
            and current.project_id == claim.project_id
            and current.plan_id == claim.plan_id
            and current.task_id == claim.task_id
            and current.task_record_id == claim.task_record_id
            and current.generation == claim.generation
            and current.owner_id == claim.owner_id
            and current.lease_token == claim.lease_token
            and current.context_digest == claim.context_digest
            and current.input_digest == claim.input_digest
            and current.target_shot_id == claim.target_shot_id
        )

    def require_owner_locked(
        self,
        claim: "AgentBackgroundClaim",
        *,
        require_live: bool,
    ) -> AgentBackgroundLeaseRecord:
        current = self._load_locked(claim.project_id, claim.plan_id, claim.task_id)
        if current is None or not self._same_owner(current, claim):
            raise AgentBackgroundLeaseStale(
                f"worker {claim.owner_id!r} no longer owns Agent Task {claim.task_id!r}"
            )
        if not current.active:
            raise AgentBackgroundLeaseStale(
                f"Agent Task {claim.task_id!r} lease is already released"
            )
        if require_live and current.is_expired(_normalized_now(self.clock)):
            raise AgentBackgroundLeaseStale(
                f"Agent Task {claim.task_id!r} lease expired before authorization"
            )
        return current

    def heartbeat(self, claim: "AgentBackgroundClaim", *, lease_seconds: float) -> AgentBackgroundLeaseRecord:
        duration = _lease_seconds(lease_seconds)
        now = _normalized_now(self.clock)
        with self.project_store._lock, self.records.project_lock(claim.project_id):
            current = self.require_owner_locked(claim, require_live=True)
            updated = replace(
                current,
                heartbeat_at=_iso(now),
                expires_at=_iso(now + timedelta(seconds=duration)),
            )
            try:
                self.records.compare_and_swap(
                    claim.project_id,
                    current.record_id,
                    expected=current.to_dict(),
                    replacement=updated.to_dict(),
                )
            except ProjectTaskRecordConflict as exc:
                raise AgentBackgroundLeaseStale("background lease changed during heartbeat") from exc
            return updated

    def release(
        self,
        claim: "AgentBackgroundClaim",
        *,
        outcome: str,
        error: Exception | None = None,
    ) -> AgentBackgroundLeaseRecord:
        if not isinstance(outcome, str) or not outcome.strip():
            raise AgentBackgroundError("lease release outcome is required")
        now = _normalized_now(self.clock)
        with self.project_store._lock, self.records.project_lock(claim.project_id):
            current = self._load_locked(claim.project_id, claim.plan_id, claim.task_id)
            if current is None or not self._same_owner(current, claim):
                raise AgentBackgroundLeaseStale("background lease changed before release")
            if not current.active:
                return current
            updated = replace(
                current,
                released_at=_iso(now),
                outcome=outcome.strip()[:200],
                error_type=(error.__class__.__name__ if error is not None else None),
                error_message=(safe_error_message(error) if error is not None else None),
            )
            try:
                self.records.compare_and_swap(
                    claim.project_id,
                    current.record_id,
                    expected=current.to_dict(),
                    replacement=updated.to_dict(),
                )
            except ProjectTaskRecordConflict as exc:
                raise AgentBackgroundLeaseStale("background lease changed before release") from exc
            return updated

    def release_record(
        self,
        record: AgentBackgroundLeaseRecord,
        *,
        outcome: str,
    ) -> AgentBackgroundLeaseRecord:
        """Release an expired/live record while state recovery holds the project task lock."""

        if not record.active:
            return record
        now = _normalized_now(self.clock)
        updated = replace(
            record,
            released_at=_iso(now),
            outcome=outcome[:200],
        )
        try:
            self.records.compare_and_swap(
                record.project_id,
                record.record_id,
                expected=record.to_dict(),
                replacement=updated.to_dict(),
            )
        except ProjectTaskRecordConflict as exc:
            raise AgentBackgroundLeaseStale("background lease changed during recovery release") from exc
        return updated


@dataclass(frozen=True)
class AgentBackgroundClaim:
    project_id: str
    plan_id: str
    task_id: str
    task_record_id: str
    action_id: str
    skill_id: str | None
    owner_id: str
    lease_record_id: str
    generation: int
    lease_token: str
    context_digest: str
    input_digest: str
    target_shot_id: str | None
    correlation_id: str
    policy: AgentPolicyProjection


_BACKGROUND_EXECUTION: ContextVar[
    tuple["AgentBackgroundTaskCoordinator", AgentBackgroundClaim] | None
] = ContextVar("uv_agent_background_execution", default=None)


@contextmanager
def _background_execution(
    coordinator: "AgentBackgroundTaskCoordinator",
    claim: AgentBackgroundClaim,
) -> Iterator[None]:
    token = _BACKGROUND_EXECUTION.set((coordinator, claim))
    try:
        yield
    finally:
        _BACKGROUND_EXECUTION.reset(token)


class _BackgroundFencedProjectUnitOfWork(_FinalCorrelatedProjectUnitOfWork):
    """Fence existing ProjectUnitOfWork commit at the worker ownership boundary."""

    def __init__(self, project_store: Any, coordinator: "AgentBackgroundTaskCoordinator") -> None:
        super().__init__(project_store)
        self._background_coordinator = coordinator

    def _execute_prepared(self, *args: Any, **kwargs: Any) -> Any:
        bound = _BACKGROUND_EXECUTION.get()
        if bound is None:
            return super()._execute_prepared(*args, **kwargs)
        coordinator, claim = bound
        if coordinator is not self._background_coordinator:
            raise AgentBackgroundLeaseStale("background commit reached the wrong coordinator fence")
        with coordinator._commit_guard(claim):
            return super()._execute_prepared(*args, **kwargs)


class _BackgroundFencedGenerationService:
    """Fence existing GenerationService.submit before D-017 consumption/Job creation."""

    def __init__(self, base: Any, coordinator: "AgentBackgroundTaskCoordinator") -> None:
        self._base = base
        self._coordinator = coordinator

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def submit(self, *args: Any, **kwargs: Any) -> Any:
        bound = _BACKGROUND_EXECUTION.get()
        if bound is None:
            return self._base.submit(*args, **kwargs)
        coordinator, claim = bound
        if coordinator is not self._coordinator:
            raise AgentBackgroundLeaseStale("background generation reached the wrong coordinator fence")
        project_id = kwargs.get("project_id")
        if project_id is None and args:
            project_id = args[0]
        if project_id != claim.project_id:
            raise AgentBackgroundLeaseStale("background generation project does not match worker claim")
        with coordinator._commit_guard(claim):
            return self._base.submit(*args, **kwargs)


class AgentBackgroundTaskCoordinator(_Stage17TaskCoordinator):
    """Background execution seam over the merged Stage-16/17 coordinator authority."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )
        self.clock = clock
        self.leases = AgentBackgroundLeaseStore(self.project_store, clock=clock)

        # Keep the same transaction authority/recovery shape, adding only a fencing
        # check immediately around the already-existing canonical commit operation.
        self._transaction_evidence = _BackgroundFencedProjectUnitOfWork(
            self.project_store,
            self,
        )
        self.harness.production.uow = self._transaction_evidence
        self.harness.timeline.unit_of_work = self._transaction_evidence

        generation = self.harness.generation
        if isinstance(generation, _BackgroundFencedGenerationService):
            generation = generation._base
        self._background_generation_base = generation
        self.harness.generation = _BackgroundFencedGenerationService(generation, self)

    def _after_lease_persisted(self, lease: AgentBackgroundLeaseRecord) -> None:
        """Fault-injection seam for proving crash between lease persistence and RUNNING."""

    def _current_context_digest(self, claim: AgentBackgroundClaim) -> str:
        snapshot = self.harness.context.build(
            claim.project_id,
            shot_id=claim.target_shot_id,
        )
        return snapshot.digest

    @contextmanager
    def _commit_guard(self, claim: AgentBackgroundClaim) -> Iterator[None]:
        """Hold the task-root fence while validating ownership and committing effect."""

        with self.project_store._lock, self.tasks.records.project_lock(claim.project_id):
            self.leases.require_owner_locked(claim, require_live=True)
            task = self.tasks.get(claim.project_id, claim.plan_id, claim.task_id)
            if task.record_id != claim.task_record_id or task.status is not AgentTaskStatus.RUNNING:
                raise AgentBackgroundLeaseStale(
                    "background worker lost the exact RUNNING Agent Task before canonical commit"
                )
            if self._current_context_digest(claim) != claim.context_digest:
                raise AgentBackgroundContextStale(
                    "canonical Agent context changed after background claim; commit refused"
                )
            yield

    def _validate_live_claim(self, claim: AgentBackgroundClaim, *, require_context: bool) -> None:
        with self.project_store._lock, self.tasks.records.project_lock(claim.project_id):
            self.leases.require_owner_locked(claim, require_live=True)
            task = self.tasks.get(claim.project_id, claim.plan_id, claim.task_id)
            if task.record_id != claim.task_record_id or task.status is not AgentTaskStatus.RUNNING:
                raise AgentBackgroundLeaseStale("background claim no longer owns a RUNNING Agent Task")
            if require_context and self._current_context_digest(claim) != claim.context_digest:
                raise AgentBackgroundContextStale(
                    "canonical Agent context changed before background dispatch"
                )

    def claim_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        owner_id: str,
        lease_seconds: float,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> AgentBackgroundClaim:
        """Atomically claim READY work and persist exact pre-dispatch evidence."""

        with self.project_store._lock, self.tasks.records.project_lock(project_id):
            plan = self.plans.get(project_id, plan_id)
            self._require_execution_reference_budget(plan)
            spec = plan.task(task_id)
            record = self.tasks.get(project_id, plan.plan_id, spec.task_id)
            if record.status is AgentTaskStatus.PLANNED:
                raise AgentTaskBlocked(
                    f"Agent Task {spec.task_id!r} is blocked by unsatisfied dependencies"
                )
            if record.status is not AgentTaskStatus.READY:
                raise AgentBackgroundLeaseConflict(
                    f"Agent Task {spec.task_id!r} is not claimable from {record.status.value!r}"
                )
            records = {
                item.task_id: item
                for item in self.tasks.list_by_plan(project_id, plan.plan_id)
            }
            unsatisfied = [
                dependency
                for dependency in spec.dependencies
                if records[dependency].status is not AgentTaskStatus.SUCCEEDED
            ]
            if unsatisfied:
                raise AgentTaskBlocked(
                    f"Agent Task {spec.task_id!r} has unsatisfied dependencies: {unsatisfied!r}"
                )

            payload = self._execution_payload(spec, runtime_inputs)
            target_shot_id = self._execution_target_shot_id(spec)
            snapshot = self.harness.context.build(project_id, shot_id=target_shot_id)
            input_digest = self._expected_input_digest(spec)
            policy = self._execution_policy(project_id, spec, payload)
            correlation_id = _typed_correlation_reference(
                plan.plan_id,
                spec.task_id,
                spec.skill_id,
            )
            lease = self.leases.claim(
                project_id=project_id,
                plan_id=plan.plan_id,
                task_id=spec.task_id,
                task_record_id=record.record_id,
                owner_id=owner_id,
                context_digest=snapshot.digest,
                input_digest=input_digest,
                target_shot_id=target_shot_id,
                lease_seconds=lease_seconds,
            )
            # Deliberately before READY -> RUNNING so a process-loss proof can leave a
            # READY task with an expiring claim that is safely reclaimable once expired.
            self._after_lease_persisted(lease)

            try:
                with _execution_correlation(correlation_id), _execution_context(snapshot.digest):
                    running = self.tasks.transition(record, AgentTaskStatus.RUNNING)
                self._execution_evidence.append(
                    project_id=project_id,
                    plan_id=plan.plan_id,
                    task_id=spec.task_id,
                    action_id=spec.action_id,
                    skill_id=spec.skill_id,
                    context_digest=snapshot.digest,
                    input_digest=input_digest,
                    policy=policy,
                )
            except Exception as exc:
                current = self.tasks.get(project_id, plan.plan_id, spec.task_id)
                if current.status is AgentTaskStatus.RUNNING:
                    self.tasks.transition(current, AgentTaskStatus.FAILED, error=exc)
                claim = AgentBackgroundClaim(
                    project_id=project_id,
                    plan_id=plan.plan_id,
                    task_id=spec.task_id,
                    task_record_id=record.record_id,
                    action_id=spec.action_id,
                    skill_id=spec.skill_id,
                    owner_id=lease.owner_id,
                    lease_record_id=lease.record_id,
                    generation=lease.generation,
                    lease_token=lease.lease_token,
                    context_digest=lease.context_digest,
                    input_digest=lease.input_digest,
                    target_shot_id=lease.target_shot_id,
                    correlation_id=correlation_id,
                    policy=policy,
                )
                try:
                    self.leases.release(claim, outcome="claim_failed", error=exc)
                except AgentBackgroundError:
                    pass
                raise

            return AgentBackgroundClaim(
                project_id=project_id,
                plan_id=plan.plan_id,
                task_id=spec.task_id,
                task_record_id=running.record_id,
                action_id=spec.action_id,
                skill_id=spec.skill_id,
                owner_id=lease.owner_id,
                lease_record_id=lease.record_id,
                generation=lease.generation,
                lease_token=lease.lease_token,
                context_digest=lease.context_digest,
                input_digest=lease.input_digest,
                target_shot_id=lease.target_shot_id,
                correlation_id=correlation_id,
                policy=policy,
            )

    def heartbeat_claim(
        self,
        claim: AgentBackgroundClaim,
        *,
        lease_seconds: float,
    ) -> AgentBackgroundLeaseRecord:
        return self.leases.heartbeat(claim, lease_seconds=lease_seconds)

    def _finalize_claim(
        self,
        claim: AgentBackgroundClaim,
        *,
        execution_error: Exception | None,
    ) -> AgentTaskRecord:
        with self.project_store._lock, self.tasks.records.project_lock(claim.project_id):
            self.leases.require_owner_locked(claim, require_live=True)
            plan = self.plans.get(claim.project_id, claim.plan_id)
            record = self.tasks.get(claim.project_id, claim.plan_id, claim.task_id)
            if record.record_id != claim.task_record_id or record.status is not AgentTaskStatus.RUNNING:
                raise AgentBackgroundLeaseStale("background Agent Task changed before finalization")

            trace = self._correlated_trace_for(plan, record)
            if trace is not None:
                if trace.status is AgentTraceStatus.SUCCEEDED:
                    terminal = self.tasks.transition(
                        record,
                        AgentTaskStatus.SUCCEEDED,
                        trace=trace,
                    )
                else:
                    error = execution_error or AgentBackgroundError(
                        trace.error_message or "background Agent execution failed"
                    )
                    terminal = self.tasks.transition(
                        record,
                        AgentTaskStatus.FAILED,
                        trace=trace,
                        error=error,
                    )
            else:
                recovered = self._committed_recovery_trace(plan, record)
                if recovered is not None:
                    # Use the Stage-17 implementation directly so recovered success is
                    # enriched with bound delegation provenance before terminalization.
                    terminal = _Stage17TaskCoordinator._reconcile_running(self, plan, record)
                else:
                    error = execution_error or AgentBackgroundError(
                        "background execution completed without trace or committed-effect evidence"
                    )
                    terminal = self.tasks.transition(
                        record,
                        AgentTaskStatus.FAILED,
                        error=error,
                    )

            self.leases.release(
                claim,
                outcome=f"task_{terminal.status.value}",
                error=(execution_error if terminal.status is AgentTaskStatus.FAILED else None),
            )
            if terminal.status is AgentTaskStatus.SUCCEEDED:
                self.tasks.promote_ready(plan)
            return terminal

    def execute_claim(
        self,
        claim: AgentBackgroundClaim,
        *,
        runtime_inputs: Mapping[str, Any] | None = None,
        heartbeat_seconds: float = 0.0,
        lease_seconds: float = 30.0,
    ) -> Any:
        """Execute one already-claimed task without holding the long task-root lock."""

        duration = _lease_seconds(lease_seconds)
        if heartbeat_seconds < 0:
            raise AgentBackgroundError("heartbeat_seconds must be non-negative")
        self._validate_live_claim(claim, require_context=True)

        with self.project_store._lock:
            plan = self.plans.get(claim.project_id, claim.plan_id)
            spec = plan.task(claim.task_id)
            if spec.action_id != claim.action_id or spec.skill_id != claim.skill_id:
                raise AgentBackgroundLeaseStale("background claim no longer matches immutable Agent Plan")
            if self._expected_input_digest(spec) != claim.input_digest:
                raise AgentBackgroundLeaseStale("background claim input digest no longer matches Agent Plan")
            if self._execution_target_shot_id(spec) != claim.target_shot_id:
                raise AgentBackgroundLeaseStale("background claim target no longer matches Agent Plan")
            payload = self._execution_payload(spec, runtime_inputs)
            model_id = payload.get("model_id")
            normalized_model_id = model_id if isinstance(model_id, str) else None
            delegation_references = self._delegation_references(plan)

        stop = threading.Event()
        heartbeat_errors: list[Exception] = []

        def heartbeat_loop() -> None:
            if heartbeat_seconds <= 0:
                return
            while not stop.wait(heartbeat_seconds):
                try:
                    self.heartbeat_claim(claim, lease_seconds=duration)
                except Exception as exc:  # background liveness is converted into fencing
                    heartbeat_errors.append(exc)
                    stop.set()
                    return

        heartbeat = threading.Thread(
            target=heartbeat_loop,
            name=f"uv-agent-heartbeat-{claim.task_id}",
            daemon=True,
        )
        heartbeat.start()

        result: Any = None
        execution_error: Exception | None = None
        try:
            with (
                self._generation_target_context.bind(claim.target_shot_id),
                self._generation_service.bind_agent_task(
                    project_id=claim.project_id,
                    plan_id=claim.plan_id,
                    task_id=claim.task_id,
                ),
                self._delegation_traces.bind(*delegation_references),
                self._correlated_traces.correlate(
                    plan.plan_id,
                    spec.task_id,
                    spec.skill_id,
                    *plan.canonical_references,
                    expected_input_digest=claim.input_digest,
                ),
                _execution_correlation(claim.correlation_id),
                _execution_context(claim.context_digest),
                self._execution_policy_catalog.bind(
                    project_id=claim.project_id,
                    action_id=claim.action_id,
                    model_id=normalized_model_id,
                    policy=claim.policy,
                ),
                _background_execution(self, claim),
            ):
                self._validate_live_claim(claim, require_context=True)
                result = self.harness.execute(
                    project_id=claim.project_id,
                    action_id=claim.action_id,
                    inputs=payload,
                    target_shot_id=claim.target_shot_id,
                )
        except Exception as exc:
            execution_error = exc
        finally:
            stop.set()
            heartbeat.join(timeout=max(1.0, heartbeat_seconds * 2 if heartbeat_seconds else 1.0))

        if heartbeat_errors:
            # Never let a worker that lost heartbeat authority finalize its own result.
            raise AgentBackgroundLeaseStale(
                f"background heartbeat lost worker ownership: {safe_error_message(heartbeat_errors[0])}"
            ) from heartbeat_errors[0]

        terminal = self._finalize_claim(claim, execution_error=execution_error)
        if execution_error is not None:
            raise execution_error
        if terminal.status is not AgentTaskStatus.SUCCEEDED:
            raise AgentBackgroundError(
                f"background Agent Task finalized as {terminal.status.value!r}"
            )
        return result

    def _reconcile_running(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTaskRecord:
        lease = self.leases.get(record.project_id, plan.plan_id, record.task_id)
        if lease is not None and lease.active and not lease.is_expired(_normalized_now(self.clock)):
            # A live background worker still owns this RUNNING task. Reopen must not
            # convert legitimate in-flight work into a failure just because another
            # reader inspected state.
            return record

        terminal = _Stage17TaskCoordinator._reconcile_running(self, plan, record)
        if lease is not None and lease.active:
            self.leases.release_record(
                lease,
                outcome=f"recovered_{terminal.status.value}",
            )
        return terminal

    def state(self, project_id: str, plan_id: str):
        state = super().state(project_id, plan_id)
        with self.project_store._lock, self.tasks.records.project_lock(project_id):
            for record in state.tasks:
                if record.status in {
                    AgentTaskStatus.SUCCEEDED,
                    AgentTaskStatus.FAILED,
                    AgentTaskStatus.CANCELLED,
                }:
                    lease = self.leases.get(project_id, plan_id, record.task_id)
                    if lease is not None and lease.active:
                        self.leases.release_record(
                            lease,
                            outcome=f"observed_{record.status.value}",
                        )
        return state

    def cancel_task(self, *, project_id: str, plan_id: str, task_id: str) -> AgentTaskRecord:
        record = super().cancel_task(project_id=project_id, plan_id=plan_id, task_id=task_id)
        with self.project_store._lock, self.tasks.records.project_lock(project_id):
            lease = self.leases.get(project_id, plan_id, task_id)
            if lease is not None and lease.active:
                self.leases.release_record(lease, outcome="task_cancelled")
        return record


class AgentBackgroundWorker:
    """One bounded worker facade; it does not poll autonomously or own a scheduler."""

    def __init__(
        self,
        coordinator: AgentBackgroundTaskCoordinator,
        *,
        worker_id: str,
        lease_seconds: float = 30.0,
        heartbeat_seconds: float | None = None,
    ) -> None:
        try:
            self.worker_id = validate_identifier(worker_id, field_name="worker_id")
        except ProjectValidationError as exc:
            raise AgentBackgroundError(str(exc)) from exc
        self.coordinator = coordinator
        self.lease_seconds = _lease_seconds(lease_seconds)
        if heartbeat_seconds is None:
            heartbeat_seconds = max(0.25, self.lease_seconds / 3.0)
        if heartbeat_seconds < 0:
            raise AgentBackgroundError("heartbeat_seconds must be non-negative")
        if heartbeat_seconds and heartbeat_seconds >= self.lease_seconds:
            raise AgentBackgroundError("heartbeat_seconds must be shorter than lease_seconds")
        self.heartbeat_seconds = float(heartbeat_seconds)

    def claim(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> AgentBackgroundClaim:
        return self.coordinator.claim_task(
            project_id=project_id,
            plan_id=plan_id,
            task_id=task_id,
            owner_id=self.worker_id,
            lease_seconds=self.lease_seconds,
            runtime_inputs=runtime_inputs,
        )

    def execute(
        self,
        claim: AgentBackgroundClaim,
        *,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        if claim.owner_id != self.worker_id:
            raise AgentBackgroundLeaseStale("worker cannot execute another worker's claim")
        return self.coordinator.execute_claim(
            claim,
            runtime_inputs=runtime_inputs,
            heartbeat_seconds=self.heartbeat_seconds,
            lease_seconds=self.lease_seconds,
        )

    def run_once(
        self,
        *,
        project_id: str,
        plan_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any | None:
        state = self.coordinator.state(project_id, plan_id)
        ready = [record for record in state.tasks if record.status is AgentTaskStatus.READY]
        if not ready:
            return None
        claim = self.claim(
            project_id=project_id,
            plan_id=plan_id,
            task_id=ready[0].task_id,
            runtime_inputs=runtime_inputs,
        )
        return self.execute(claim, runtime_inputs=runtime_inputs)

    def run_until_blocked(
        self,
        *,
        project_id: str,
        plan_id: str,
        max_tasks: int = MAX_BACKGROUND_TASK_BUDGET,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> tuple[Any, ...]:
        if isinstance(max_tasks, bool) or not isinstance(max_tasks, int) or not 1 <= max_tasks <= MAX_BACKGROUND_TASK_BUDGET:
            raise AgentBackgroundError(
                f"max_tasks must be an integer in 1..{MAX_BACKGROUND_TASK_BUDGET}"
            )
        results: list[Any] = []
        for _ in range(max_tasks):
            state = self.coordinator.state(project_id, plan_id)
            ready = [record for record in state.tasks if record.status is AgentTaskStatus.READY]
            if not ready:
                break
            claim = self.claim(
                project_id=project_id,
                plan_id=plan_id,
                task_id=ready[0].task_id,
                runtime_inputs=runtime_inputs,
            )
            results.append(self.execute(claim, runtime_inputs=runtime_inputs))
        return tuple(results)


__all__ = [
    "AGENT_BACKGROUND_LEASE_SCHEMA_VERSION",
    "AgentBackgroundClaim",
    "AgentBackgroundContextStale",
    "AgentBackgroundError",
    "AgentBackgroundLeaseConflict",
    "AgentBackgroundLeaseRecord",
    "AgentBackgroundLeaseStale",
    "AgentBackgroundLeaseStore",
    "AgentBackgroundRetryLimit",
    "AgentBackgroundTaskCoordinator",
    "AgentBackgroundWorker",
    "MAX_BACKGROUND_CLAIMS_PER_TASK",
    "MAX_BACKGROUND_TASK_BUDGET",
]
