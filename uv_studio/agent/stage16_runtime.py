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

from .models import AgentHarnessError, AgentTraceRecord
from .orchestration import (
    AGENT_PLAN_RECORD_TYPE,
    AgentPlanExecutionState as _BaseAgentPlanExecutionState,
    AgentPlanRecord,
    AgentPlanStatus,
    AgentPlanStore as _BaseAgentPlanStore,
    AgentPlanner,
    AgentPlanningError,
    AgentSkillCatalog as _BaseAgentSkillCatalog,
    AgentTaskCoordinator as _BaseAgentTaskCoordinator,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
    AgentTaskStore as _BaseAgentTaskStore,
)

AGENT_SKILL_SCHEMA_VERSION = 1


class AgentSkillCatalog(_BaseAgentSkillCatalog):
    """Public Skill catalog with stable schema metadata around bounded Skills."""

    schema_version = AGENT_SKILL_SCHEMA_VERSION

    def describe(self, skill_id: str) -> dict[str, Any]:
        result = super().describe(skill_id)
        return {"schema_version": self.schema_version, **result}


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
    """Recoverably initialize the task set described by an append-only plan."""

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

            # If a partial initial write was interrupted after dependencies later
            # completed, promote any newly reconstructed dependent records normally.
            return super().promote_ready(plan)

    def initialize(self, plan: AgentPlanRecord) -> tuple[AgentTaskRecord, ...]:
        return self.ensure_initialized(plan)


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
    """Proxy the existing append-only trace store with bounded orchestration refs."""

    def __init__(self, base: Any) -> None:
        self._base = base
        self._correlation: ContextVar[tuple[str, ...]] = ContextVar(
            f"uv_agent_trace_correlation_{id(self)}",
            default=(),
        )

    @contextmanager
    def correlate(self, *references: str | None) -> Iterator[None]:
        normalized = tuple(
            dict.fromkeys(
                reference for reference in references if isinstance(reference, str) and reference
            )
        )
        token = self._correlation.set(normalized)
        try:
            yield
        finally:
            self._correlation.reset(token)

    def append(self, record: AgentTraceRecord):
        correlation = self._correlation.get()
        if not correlation:
            return self._base.append(record)
        references = tuple(dict.fromkeys((*record.canonical_references, *correlation)))
        return self._base.append(replace(record, canonical_references=references))

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

    def state(self, project_id: str, plan_id: str) -> AgentPlanExecutionState:
        """Reopen fail-closed and repair only missing initial task records."""

        with self.project_store._lock:
            plan = self.plans.get(project_id, plan_id)
            if isinstance(self.tasks, AgentTaskStore):
                self.tasks.ensure_initialized(plan)
            for record in self.tasks.list_by_plan(project_id, plan.plan_id):
                if record.status is not AgentTaskStatus.RUNNING:
                    continue
                interruption = AgentTaskStateError(
                    "Agent Task was interrupted before durable completion; automatic replay is disabled"
                )
                self.tasks.transition(record, AgentTaskStatus.FAILED, error=interruption)
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

        with self._correlated_traces.correlate(plan.plan_id, spec.task_id, spec.skill_id):
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
