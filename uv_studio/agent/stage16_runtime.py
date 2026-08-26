"""Stage-16 runtime refinements over durable Agent planning/task contracts.

The refinements remain above the same Stage-15 AgentHarness authority. They add
recoverable durable initialization, complete plan discovery, fail-closed restart
reconciliation, stable Skill metadata, derived plan inspection, trace correlation
and execution-only authorization defaults without a second project/trace authority.
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from typing import Any, Iterator, Mapping, Sequence

from uv_studio.projects.models import utc_now_iso

from .models import (
    AgentHarnessError,
    AgentTraceRecord,
    AgentTraceStatus,
    portable_json,
    safe_error_message,
    stable_digest,
)
from .orchestration import (
    AGENT_PLAN_RECORD_TYPE,
    AgentPlanExecutionState as _BaseAgentPlanExecutionState,
    AgentPlanRecord,
    AgentPlanStatus,
    AgentPlanStepProposal,
    AgentPlanStore as _BaseAgentPlanStore,
    AgentPlanner as _BaseAgentPlanner,
    AgentPlanningError,
    AgentSkillCatalog as _BaseAgentSkillCatalog,
    AgentTaskCoordinator as _BaseAgentTaskCoordinator,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
    AgentTaskStore as _BaseAgentTaskStore,
)

AGENT_SKILL_SCHEMA_VERSION = 1


def _typed_correlation_reference(
    plan_id: str,
    task_id: str,
    skill_id: str | None,
) -> str:
    digest = stable_digest(
        {
            "record_type": "agent_task_correlation",
            "plan_id": plan_id,
            "task_id": task_id,
            "skill_id": skill_id,
        }
    )
    return f"agent_corr_{digest[:32]}"


class AgentSkillCatalog(_BaseAgentSkillCatalog):
    """Public Skill catalog with stable schema metadata around bounded Skills."""

    schema_version = AGENT_SKILL_SCHEMA_VERSION

    def describe(self, skill_id: str) -> dict[str, Any]:
        result = super().describe(skill_id)
        return {"schema_version": self.schema_version, **result}


class AgentPlanner(_BaseAgentPlanner):
    """Bind every effective task target into validated deterministic plan context."""

    def build(
        self,
        *,
        project_id: str,
        goal: str,
        proposals: Sequence[AgentPlanStepProposal],
        target_shot_id: str | None = None,
        canonical_references: Sequence[str] = (),
        plan_id: str | None = None,
    ) -> AgentPlanRecord:
        plan = super().build(
            project_id=project_id,
            goal=goal,
            proposals=proposals,
            target_shot_id=target_shot_id,
            canonical_references=canonical_references,
            plan_id=plan_id,
        )

        effective_targets = tuple(
            sorted(
                {
                    task.target_shot_id
                    for task in plan.tasks
                    if task.target_shot_id is not None
                }
            )
        )
        if not effective_targets:
            return plan

        snapshots = []
        for shot_id in effective_targets:
            try:
                snapshots.append(self.harness.context.build(project_id, shot_id=shot_id))
            except Exception as exc:
                raise AgentPlanningError(
                    f"could not bind target shot {shot_id!r}: {safe_error_message(exc)}"
                ) from exc

        if len(snapshots) == 1:
            context_digest = snapshots[0].digest
        else:
            context_digest = stable_digest(
                {
                    "target_contexts": [
                        {
                            "target_id": snapshot.target_id,
                            "digest": snapshot.digest,
                        }
                        for snapshot in snapshots
                    ]
                }
            )
        references = tuple(
            dict.fromkeys(
                (
                    *plan.canonical_references,
                    *(snapshot.target_id for snapshot in snapshots),
                )
            )
        )
        return replace(
            plan,
            context_digest=context_digest,
            canonical_references=references,
        )


class AgentPlanStore(_BaseAgentPlanStore):
    """Discover every durable Agent plan by record type, not filename prefix."""

    def list(self, project_id: str) -> tuple[AgentPlanRecord, ...]:
        with self.project_store._lock:
            project_dir = self.project_store.project_directory(project_id)
            plans: list[AgentPlanRecord] = []
            for path in sorted((project_dir / "tasks").glob("*.json"), key=lambda item: item.name):
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    raise AgentPlanningError(
                        f"invalid project task record {path.name!r} while listing Agent plans: {exc}"
                    ) from exc
                if not isinstance(raw, Mapping) or raw.get("record_type") != AGENT_PLAN_RECORD_TYPE:
                    continue
                try:
                    plan = AgentPlanRecord.from_dict(raw)
                except AgentHarnessError as exc:
                    raise AgentPlanningError(
                        f"invalid Agent plan record {path.name!r}: {exc}"
                    ) from exc
                if plan.project_id != project_id or plan.plan_id != path.stem:
                    raise AgentPlanningError("Agent plan record identity mismatch")
                plans.append(plan)
            plans.sort(key=lambda item: (item.created_at, item.plan_id))
            return tuple(plans)


class AgentTaskStore(_BaseAgentTaskStore):
    """Recoverable initialization plus compare-and-swap durable transitions."""

    @staticmethod
    def _initial_record(plan: AgentPlanRecord, spec: Any, *, now: str) -> AgentTaskRecord:
        return AgentTaskRecord(
            record_id=f"agent_task_{uuid.uuid4().hex}",
            task_id=spec.task_id,
            plan_id=plan.plan_id,
            project_id=plan.project_id,
            action_id=spec.action_id,
            skill_id=spec.skill_id,
            status=(AgentTaskStatus.READY if not spec.dependencies else AgentTaskStatus.PLANNED),
            created_at=now,
            updated_at=now,
        )

    def ensure_initialized(self, plan: AgentPlanRecord) -> tuple[AgentTaskRecord, ...]:
        """Complete a missing/partial initial task set after interruption.

        A plan is immutable and authoritative for task identities. Missing task
        records can therefore be recreated deterministically as initial orchestration
        state. Existing records are never reset or replayed.
        """

        with self.project_store._lock:
            existing = self.list_by_plan(plan.project_id, plan.plan_id)
            by_id: dict[str, AgentTaskRecord] = {}
            for record in existing:
                if record.task_id in by_id:
                    raise AgentTaskStateError(
                        f"duplicate durable Agent Task identity: {record.task_id!r}"
                    )
                by_id[record.task_id] = record

            specs = {spec.task_id: spec for spec in plan.tasks}
            unexpected = set(by_id).difference(specs)
            if unexpected:
                raise AgentTaskStateError(
                    f"durable Agent Task set contains identities outside plan: {sorted(unexpected)!r}"
                )
            for task_id, record in by_id.items():
                spec = specs[task_id]
                if record.action_id != spec.action_id or record.skill_id != spec.skill_id:
                    raise AgentTaskStateError(
                        f"durable Agent Task {task_id!r} no longer matches immutable plan"
                    )

            now = utc_now_iso()
            for spec in plan.tasks:
                if spec.task_id in by_id:
                    continue
                record = self._initial_record(plan, spec, now=now)
                self.records.write(plan.project_id, record.record_id, record.to_dict())
                by_id[spec.task_id] = record

            return super().promote_ready(plan)

    def initialize(self, plan: AgentPlanRecord) -> tuple[AgentTaskRecord, ...]:
        return self.ensure_initialized(plan)

    def transition(
        self,
        record: AgentTaskRecord,
        status: AgentTaskStatus,
        *,
        trace: AgentTraceRecord | None = None,
        error: Exception | None = None,
    ) -> AgentTaskRecord:
        """Apply one transition only to the exact durable snapshot supplied.

        The full immutable record acts as the compare-and-swap version. A caller
        holding a stale READY/PLANNED/RUNNING snapshot cannot overwrite a newer
        durable status, timestamps, trace binding, result references, or error.
        """

        with self.project_store._lock:
            current = super().get(record.project_id, record.plan_id, record.task_id)
            if current.record_id != record.record_id:
                raise AgentTaskStateError(
                    f"stale Agent Task snapshot has replaced record identity: {record.task_id!r}"
                )
            if current != record:
                raise AgentTaskStateError(
                    f"stale Agent Task snapshot for {record.task_id!r}; reload durable state"
                )
            return super().transition(
                current,
                status,
                trace=trace,
                error=error,
            )


class AgentPlanExecutionState(_BaseAgentPlanExecutionState):
    """Derived durable inspection view over append-only plan + mutable task state."""

    @property
    def created_at(self) -> str:
        return self.plan.created_at

    @property
    def updated_at(self) -> str:
        values = [self.plan.created_at]
        values.extend(task.updated_at for task in self.tasks)
        return max(values)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["created_at"] = self.created_at
        result["updated_at"] = self.updated_at
        return result


class _CorrelatingTraceStore:
    """Proxy the existing append-only trace store with typed orchestration refs."""

    def __init__(self, base: Any) -> None:
        self._base = base
        self._correlation: ContextVar[tuple[str, ...]] = ContextVar(
            f"uv_agent_trace_correlation_{id(self)}",
            default=(),
        )
        self._expected_input_digest: ContextVar[str | None] = ContextVar(
            f"uv_agent_expected_input_digest_{id(self)}",
            default=None,
        )

    @contextmanager
    def correlate(
        self,
        *references: str | None,
        expected_input_digest: str | None = None,
    ) -> Iterator[None]:
        normalized = list(
            dict.fromkeys(
                reference for reference in references if isinstance(reference, str) and reference
            )
        )
        if len(references) >= 2:
            plan_id = references[0]
            task_id = references[1]
            skill_id = references[2] if len(references) >= 3 else None
            if isinstance(plan_id, str) and plan_id and isinstance(task_id, str) and task_id:
                typed = _typed_correlation_reference(
                    plan_id,
                    task_id,
                    skill_id if isinstance(skill_id, str) and skill_id else None,
                )
                if typed not in normalized:
                    normalized.append(typed)
        correlation_token = self._correlation.set(tuple(normalized))
        digest_token = self._expected_input_digest.set(expected_input_digest)
        try:
            yield
        finally:
            self._expected_input_digest.reset(digest_token)
            self._correlation.reset(correlation_token)

    def append(self, record: AgentTraceRecord):
        correlation = self._correlation.get()
        if not correlation:
            return self._base.append(record)

        references = tuple(dict.fromkeys((*record.canonical_references, *correlation)))
        replacement = replace(record, canonical_references=references)

        expected_input_digest = self._expected_input_digest.get()
        if (
            expected_input_digest is not None
            and record.status is AgentTraceStatus.FAILED
            and record.error_type is not None
        ):
            preparation_failure_digest = stable_digest(
                {
                    "rejected_inputs": True,
                    "error_type": record.error_type,
                }
            )
            if record.input_digest == preparation_failure_digest:
                replacement = replace(replacement, input_digest=expected_input_digest)

        return self._base.append(replacement)

    def list(self, project_id: str) -> tuple[AgentTraceRecord, ...]:
        return self._base.list(project_id)


class AgentTaskCoordinator(_BaseAgentTaskCoordinator):
    """Public Stage-16 coordinator with durable recovery and inspection refinements."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        if planner is None:
            planner = AgentPlanner(harness, skills=AgentSkillCatalog(harness.catalog))
        if plan_store is None:
            plan_store = AgentPlanStore(harness.project_store)
        if task_store is None:
            task_store = AgentTaskStore(harness.project_store)
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )
        current = self.harness.traces
        if isinstance(current, _CorrelatingTraceStore):
            self._correlated_traces = current
        else:
            correlated = _CorrelatingTraceStore(current)
            self.harness.traces = correlated
            self._correlated_traces = correlated

    @staticmethod
    def _plan_status(records: Sequence[AgentTaskRecord]) -> AgentPlanStatus:
        if records and all(record.status is AgentTaskStatus.SUCCEEDED for record in records):
            return AgentPlanStatus.SUCCEEDED
        if any(record.status is AgentTaskStatus.FAILED for record in records):
            return AgentPlanStatus.FAILED
        if any(record.status is AgentTaskStatus.RUNNING for record in records):
            return AgentPlanStatus.RUNNING
        terminal = {AgentTaskStatus.SUCCEEDED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED}
        if records and all(record.status in terminal for record in records):
            return AgentPlanStatus.CANCELLED
        return AgentPlanStatus.ACTIVE

    @staticmethod
    def _expected_input_digest(spec: Any) -> str:
        return stable_digest(
            {
                "action_id": spec.action_id,
                "inputs": portable_json(spec.inputs, field_name="Agent action inputs"),
            }
        )

    def _correlated_trace_for(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTraceRecord | None:
        spec = plan.task(record.task_id)
        typed_reference = _typed_correlation_reference(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
        )
        expected_input_digest = self._expected_input_digest(spec)
        candidates = [
            trace
            for trace in self.harness.traces.list(record.project_id)
            if trace.action_id == record.action_id
            and typed_reference in trace.canonical_references
            and trace.input_digest == expected_input_digest
            and (record.started_at is None or trace.created_at >= record.started_at)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.created_at, item.trace_id))
        return candidates[-1]

    def _reconcile_running(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTaskRecord:
        trace = self._correlated_trace_for(plan, record)
        if trace is not None:
            if trace.status is AgentTraceStatus.SUCCEEDED:
                return self.tasks.transition(record, AgentTaskStatus.SUCCEEDED, trace=trace)
            error = AgentTaskStateError(
                trace.error_message or "Agent Task execution failed before durable task completion"
            )
            return self.tasks.transition(
                record,
                AgentTaskStatus.FAILED,
                trace=trace,
                error=error,
            )
        interruption = AgentTaskStateError(
            "Agent Task was interrupted before durable completion; automatic replay is disabled"
        )
        return self.tasks.transition(record, AgentTaskStatus.FAILED, error=interruption)

    def state(self, project_id: str, plan_id: str) -> AgentPlanExecutionState:
        """Reopen fail-closed, reconcile traces and repair missing initial tasks."""

        with self.project_store._lock:
            plan = self.plans.get(project_id, plan_id)
            if isinstance(self.tasks, AgentTaskStore):
                self.tasks.ensure_initialized(plan)
            for record in self.tasks.list_by_plan(project_id, plan.plan_id):
                if record.status is AgentTaskStatus.RUNNING:
                    self._reconcile_running(plan, record)
            self.tasks.promote_ready(plan)
            state = super().state(project_id, plan.plan_id)
            return AgentPlanExecutionState(plan=state.plan, tasks=state.tasks, status=state.status)

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        plan = self.plans.get(project_id, plan_id)
        spec = plan.task(task_id)
        definition = self.harness.catalog.get(spec.action_id)

        effective_runtime_inputs = runtime_inputs
        if "authorization_token" in definition.input_fields:
            if runtime_inputs is None:
                effective_runtime_inputs = {"authorization_token": None}
            elif "authorization_token" not in runtime_inputs:
                effective_runtime_inputs = dict(runtime_inputs)
                effective_runtime_inputs["authorization_token"] = None

        expected_input_digest = self._expected_input_digest(spec)
        with self._correlated_traces.correlate(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
            expected_input_digest=expected_input_digest,
        ):
            return super().execute_task(
                project_id=project_id,
                plan_id=plan.plan_id,
                task_id=spec.task_id,
                runtime_inputs=effective_runtime_inputs,
            )

    def cancel_task(self, *, project_id: str, plan_id: str, task_id: str) -> AgentTaskRecord:
        """Cancel one task and transitively cancel planned dependents it makes impossible."""

        with self.project_store._lock:
            selected = super().cancel_task(
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
            )
            plan = self.plans.get(project_id, plan_id)
            changed = True
            while changed:
                changed = False
                records = {
                    record.task_id: record
                    for record in self.tasks.list_by_plan(project_id, plan.plan_id)
                }
                for spec in plan.tasks:
                    record = records[spec.task_id]
                    if record.status is not AgentTaskStatus.PLANNED:
                        continue
                    if any(
                        records[dependency].status is AgentTaskStatus.CANCELLED
                        for dependency in spec.dependencies
                    ):
                        self.tasks.transition(record, AgentTaskStatus.CANCELLED)
                        changed = True
            return selected
