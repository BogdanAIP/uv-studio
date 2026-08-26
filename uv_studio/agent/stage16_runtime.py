"""Stage-16 execution refinements over the durable Agent Task coordinator.

This module keeps one Stage-15 AgentTraceStore and one AgentHarness execution path.
It only adds orchestration correlation before append and supplies the execution-only
``authorization_token=None`` default required by GenerationService.submit when a
plan intentionally persists no authorization token.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from typing import Any, Iterator, Mapping

from .models import AgentTraceRecord
from .orchestration import AgentTaskCoordinator as _BaseAgentTaskCoordinator


class _CorrelatingTraceStore:
    """Proxy the existing append-only trace store with bounded correlation refs."""

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
    """Public Stage-16 coordinator with trace correlation and execution-only auth."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        current = self.harness.traces
        if isinstance(current, _CorrelatingTraceStore):
            self._correlated_traces = current
        else:
            correlated = _CorrelatingTraceStore(current)
            self.harness.traces = correlated
            self._correlated_traces = correlated

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
