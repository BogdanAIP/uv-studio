"""Bind generation tasks to one Shot and validate terminal task provenance.

A generation task may depend on an earlier task that creates its input Shot, so the
Shot cannot always be validated as a planner-time target. Deferred validation is
therefore permitted only when the task's dependency closure creates that same Shot.
The public Stage-16 AgentTaskStore also accepts terminal trace evidence only when it
is the exact durable Stage-15 trace correlated to the immutable Agent Task.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping, Sequence

from .harness import AgentTraceStore
from .models import AgentTraceRecord, AgentTraceStatus, portable_json, stable_digest
from .orchestration import (
    AgentPlanRecord,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_generation_policy import (
    AgentPlanner as _GenerationPolicyAgentPlanner,
    AgentTaskCoordinator as _GenerationPolicyAgentTaskCoordinator,
)
from .stage16_runtime import (
    AgentPlanStore,
    AgentSkillCatalog,
    AgentTaskStore as _RuntimeAgentTaskStore,
    _typed_correlation_reference,
)


class _GenerationTargetContext:
    """Delegate context building while supplying one execution-only Shot target."""

    def __init__(self, base: Any) -> None:
        self._base = base
        self._bound_shot_id: ContextVar[str | None] = ContextVar(
            f"uv_agent_generation_target_{id(self)}",
            default=None,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    @contextmanager
    def bind(self, shot_id: str | None) -> Iterator[None]:
        token = self._bound_shot_id.set(shot_id)
        try:
            yield
        finally:
            self._bound_shot_id.reset(token)

    def build(self, project_id: str, shot_id: str | None = None):
        effective_shot_id = shot_id if shot_id is not None else self._bound_shot_id.get()
        return self._base.build(project_id, shot_id=effective_shot_id)


class AgentPlanner(_GenerationPolicyAgentPlanner):
    """Require one resolvable generation Shot, with bounded deferred creation."""

    @staticmethod
    def _dependency_creates_shot(
        plan: AgentPlanRecord,
        spec: Any,
        shot_id: str,
    ) -> bool:
        by_id = {task.task_id: task for task in plan.tasks}
        pending = list(spec.dependencies)
        visited: set[str] = set()
        while pending:
            dependency_id = pending.pop()
            if dependency_id in visited:
                continue
            visited.add(dependency_id)
            dependency = by_id[dependency_id]
            if (
                dependency.action_id == "production.create_shot"
                and dependency.inputs.get("shot_id") == shot_id
            ):
                return True
            pending.extend(dependency.dependencies)
        return False

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
        for spec in plan.tasks:
            if spec.action_id != "generation.submit":
                continue
            shot_id = spec.inputs.get("shot_id")
            if not isinstance(shot_id, str) or not shot_id:
                raise AgentPlanningError(
                    "generation.submit lost its required input Shot identity"
                )
            if spec.target_shot_id is not None:
                if spec.target_shot_id != shot_id:
                    raise AgentPlanningError(
                        "generation.submit target_shot_id must match inputs['shot_id']"
                    )
                continue

            try:
                self.harness.production.state(project_id).shot(shot_id)
            except Exception as exc:
                if not self._dependency_creates_shot(plan, spec, shot_id):
                    raise AgentPlanningError(
                        "generation.submit input Shot must already exist or be created "
                        "by its dependency closure"
                    ) from exc
        return plan


class AgentTaskStore(_RuntimeAgentTaskStore):
    """Public Stage-16 task store with terminal trace provenance validation."""

    @staticmethod
    def _expected_input_digest(spec: Any) -> str:
        return stable_digest(
            {
                "action_id": spec.action_id,
                "inputs": portable_json(spec.inputs, field_name="Agent action inputs"),
            }
        )

    def _validate_terminal_trace(
        self,
        current: AgentTaskRecord,
        target: AgentTaskStatus,
        trace: AgentTraceRecord,
    ) -> None:
        if target not in {AgentTaskStatus.SUCCEEDED, AgentTaskStatus.FAILED}:
            raise AgentTaskStateError(
                "Agent Task trace evidence is only valid for terminal execution transitions"
            )
        if trace.project_id != current.project_id:
            raise AgentTaskStateError("Agent Task trace project provenance mismatch")
        if trace.action_id != current.action_id:
            raise AgentTaskStateError("Agent Task trace action provenance mismatch")

        expected_status = (
            AgentTraceStatus.SUCCEEDED
            if target is AgentTaskStatus.SUCCEEDED
            else AgentTraceStatus.FAILED
        )
        if trace.status is not expected_status:
            raise AgentTaskStateError(
                "Agent Task terminal status does not match Stage-15 trace status"
            )

        plan = AgentPlanStore(self.project_store).get(
            current.project_id,
            current.plan_id,
        )
        spec = plan.task(current.task_id)
        if spec.action_id != current.action_id or spec.skill_id != current.skill_id:
            raise AgentTaskStateError(
                "Agent Task trace validation disagrees with immutable plan identity"
            )

        typed_reference = _typed_correlation_reference(
            current.plan_id,
            current.task_id,
            current.skill_id,
        )
        if typed_reference not in trace.canonical_references:
            raise AgentTaskStateError(
                "Agent Task trace is missing typed task correlation provenance"
            )
        if trace.input_digest != self._expected_input_digest(spec):
            raise AgentTaskStateError("Agent Task trace input provenance mismatch")
        if current.started_at is not None and trace.created_at < current.started_at:
            raise AgentTaskStateError("Agent Task trace predates this execution attempt")

        durable_matches = [
            item
            for item in AgentTraceStore(self.project_store).list(current.project_id)
            if item.trace_id == trace.trace_id
        ]
        if len(durable_matches) != 1 or durable_matches[0] != trace:
            raise AgentTaskStateError(
                "Agent Task trace is not the exact durable Stage-15 trace record"
            )

    def transition(
        self,
        record: AgentTaskRecord,
        status: AgentTaskStatus,
        *,
        trace: AgentTraceRecord | None = None,
        error: Exception | None = None,
    ) -> AgentTaskRecord:
        target = status if isinstance(status, AgentTaskStatus) else AgentTaskStatus(status)
        current = self.get(record.project_id, record.plan_id, record.task_id)
        if target is AgentTaskStatus.SUCCEEDED and trace is None:
            raise AgentTaskStateError(
                "succeeded Agent Task transition requires correlated durable trace evidence"
            )
        if trace is not None:
            self._validate_terminal_trace(current, target, trace)
        return super().transition(
            record,
            target,
            trace=trace,
            error=error,
        )


class AgentTaskCoordinator(_GenerationPolicyAgentTaskCoordinator):
    """Final Stage-16 coordinator with one generation Shot and validated task traces."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        current_context = harness.context
        if isinstance(current_context, _GenerationTargetContext):
            self._generation_target_context = current_context
        else:
            self._generation_target_context = _GenerationTargetContext(current_context)
            harness.context = self._generation_target_context
        if planner is None:
            planner = AgentPlanner(
                harness,
                skills=AgentSkillCatalog(harness.catalog),
            )
        if task_store is None:
            task_store = AgentTaskStore(harness.project_store)
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )

    @staticmethod
    def _execution_target_shot_id(spec: Any) -> str | None:
        if spec.action_id != "generation.submit":
            return spec.target_shot_id
        shot_id = spec.inputs.get("shot_id")
        if not isinstance(shot_id, str) or not shot_id:
            raise AgentTaskStateError(
                "durable generation task lost its input Shot identity"
            )
        if spec.target_shot_id is not None and spec.target_shot_id != shot_id:
            raise AgentTaskStateError(
                "durable generation task target Shot does not match its input Shot"
            )
        return shot_id

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        with self.project_store._lock:
            plan = self.plans.get(project_id, plan_id)
            spec = plan.task(task_id)
            target_shot_id = self._execution_target_shot_id(spec)

        with self._generation_target_context.bind(target_shot_id):
            return super().execute_task(
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
                runtime_inputs=runtime_inputs,
            )


__all__ = ["AgentPlanner", "AgentTaskCoordinator", "AgentTaskStore"]
