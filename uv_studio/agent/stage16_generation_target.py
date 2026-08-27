"""Bind generation tasks to their input Shot at execution time.

A generation task may depend on an earlier task that creates its input Shot, so the
Shot cannot always be validated as a planner-time target. This final Stage-16 layer
keeps the durable Plan unchanged and binds the already-validated generation
``inputs['shot_id']`` only while that task executes. The existing AgentContextBuilder
and AgentHarness remain the canonical context/trace authorities.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping

from .orchestration import AgentTaskStateError
from .stage16_generation_policy import (
    AgentPlanner,
    AgentTaskCoordinator as _GenerationPolicyAgentTaskCoordinator,
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


class AgentTaskCoordinator(_GenerationPolicyAgentTaskCoordinator):
    """Final Stage-16 coordinator with deferred generation Shot binding."""

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
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )

    @staticmethod
    def _execution_target_shot_id(spec: Any) -> str | None:
        if spec.target_shot_id is not None:
            return spec.target_shot_id
        if spec.action_id != "generation.submit":
            return None
        shot_id = spec.inputs.get("shot_id")
        if not isinstance(shot_id, str) or not shot_id:
            raise AgentTaskStateError(
                "durable generation task lost its input Shot identity"
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
