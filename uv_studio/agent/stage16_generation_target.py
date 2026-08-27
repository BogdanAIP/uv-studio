"""Bind generation tasks to exactly one canonical Shot identity.

A generation task may depend on an earlier task that creates its input Shot, so the
Shot cannot always be validated as a planner-time target. This final Stage-16 layer
keeps the durable Plan unchanged for deferred targets, but requires any explicit
``target_shot_id`` to match the already-validated ``inputs['shot_id']``. The same
identity then scopes AgentContextBuilder, AgentHarness trace and Generation Job work.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping, Sequence

from .orchestration import (
    AgentPlanRecord,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentTaskStateError,
)
from .stage16_generation_policy import (
    AgentPlanner as _GenerationPolicyAgentPlanner,
    AgentTaskCoordinator as _GenerationPolicyAgentTaskCoordinator,
)
from .stage16_runtime import AgentSkillCatalog


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
    """Reject generation plans that name two different target Shots."""

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
            if spec.action_id != "generation.submit" or spec.target_shot_id is None:
                continue
            shot_id = spec.inputs.get("shot_id")
            if not isinstance(shot_id, str) or not shot_id:
                raise AgentPlanningError(
                    "generation.submit lost its required input Shot identity"
                )
            if spec.target_shot_id != shot_id:
                raise AgentPlanningError(
                    "generation.submit target_shot_id must match inputs['shot_id']"
                )
        return plan


class AgentTaskCoordinator(_GenerationPolicyAgentTaskCoordinator):
    """Final Stage-16 coordinator with one generation Shot identity."""

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


__all__ = ["AgentPlanner", "AgentTaskCoordinator"]