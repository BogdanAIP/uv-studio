"""Stage-16 runtime refinements over the durable Agent Task coordinator.

This module keeps one Stage-15 AgentTraceStore and one AgentHarness execution path.
It adds orchestration correlation before trace append, a stable Skill schema envelope,
derived plan inspection timestamps/status, fail-closed restart reconciliation for
abandoned running tasks, and execution-only authorization defaults.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from typing import Any, Iterator, Mapping

from .models import AgentTraceRecord
from .orchestration import (
    AgentPlanExecutionState as _BaseAgentPlanExecutionState,
    AgentPlanner,
    AgentSkillCatalog as _BaseAgentSkillCatalog,
    AgentTaskCoordinator as _BaseAgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
)

AGENT_SKILL_SCHEMA_VERSION = 1


class AgentSkillCatalog(_BaseAgentSkillCatalog):
    """Public Skill catalog with stable schema metadata around bounded Skills."""

    schema_version = AGENT_SKILL_SCHEMA_VERSION

    def describe(self, skill_id: str) -> dict[str, Any]:
        result = super().describe(skill_id)
        return {
            "schema_version": self.schema_version,
            **result,
        }


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
                reference
                for reference in references
                if isinstance(reference, str) and reference
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
        references = tuple(
            dict.fromkeys((*record.canonical_references, *correlation))
        )
        return self._base.append(
            replace(record, canonical_references=references)
        )

    def list(self, project_id: str) -> tuple[AgentTraceRecord, ...]:
        return self._base.list(project_id)


class AgentTaskCoordinator(_BaseAgentTaskCoordinator):
    """Public Stage-16 coordinator with restart, trace and auth refinements."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        if planner is None:
            planner = AgentPlanner(
                harness,
                skills=AgentSkillCatalog(harness.catalog),
            )
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

    def state(self, project_id: str, plan_id: str) -> AgentPlanExecutionState:
        """Reopen a plan fail-closed: abandoned running tasks are never replayed."""

        with self.project_store._lock:
            plan = self.plans.get(project_id, plan_id)
            for record in self.tasks.list_by_plan(project_id, plan.plan_id):
                if record.status is not AgentTaskStatus.RUNNING:
                    continue
                interruption = AgentTaskStateError(
                    "Agent Task was interrupted before durable completion; automatic replay is disabled"
                )
                self.tasks.transition(
                    record,
                    AgentTaskStatus.FAILED,
                    error=interruption,
                )
            state = super().state(project_id, plan.plan_id)
            return AgentPlanExecutionState(
                plan=state.plan,
                tasks=state.tasks,
                status=state.status,
            )

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

        with self._correlated_traces.correlate(
            plan.plan_id,
            spec.task_id,
            spec.skill_id,
        ):
            return super().execute_task(
                project_id=project_id,
                plan_id=plan.plan_id,
                task_id=spec.task_id,
                runtime_inputs=effective_runtime_inputs,
            )
