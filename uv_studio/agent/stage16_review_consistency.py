"""Final Stage-16 review consistency over durable execution evidence.

This layer keeps policy capture fail-closed before dispatch, makes recovered context
independent of the concrete injected AgentTaskStore implementation, restores the
affected Shot identity for production.accept_take, and binds AgentHarness to the
exact policy snapshot persisted for the execution.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping, Sequence

from .models import AgentPolicyProjection, AgentTraceRecord, AgentTraceStatus
from .orchestration import (
    AgentPlanRecord,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentTaskBlocked,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_execution_evidence import (
    AgentPlanner as _EvidenceAgentPlanner,
    AgentTaskCoordinator as _EvidenceAgentTaskCoordinator,
)
from .stage16_recovery import (
    _execution_context,
    _execution_correlation,
    _typed_correlation_reference,
)

# AgentPlanRecord and AgentTaskRecord each allow at most 128 canonical references.
# Execution adds bounded Stage-15 result/affected identities plus plan/task/Skill
# correlation and recovery context. Keep a conservative 16-reference reserve so a
# valid Plan can always reach a bounded terminal Task after canonical/cost-bearing
# dispatch instead of discovering the record bound after the effect has committed.
EXECUTION_SAFE_PLAN_REFERENCE_LIMIT = 112


class AgentPlanner(_EvidenceAgentPlanner):
    """Keep durable Plan provenance inside the later Task/Trace execution budget."""

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
        if len(plan.canonical_references) > EXECUTION_SAFE_PLAN_REFERENCE_LIMIT:
            raise AgentPlanningError(
                "plan canonical references exceed the execution-safe limit of "
                f"{EXECUTION_SAFE_PLAN_REFERENCE_LIMIT}"
            )
        return plan


class _ExecutionPolicyCatalog:
    """Delegate the catalog while freezing one already-captured policy for dispatch."""

    def __init__(self, base: Any) -> None:
        self._base = base
        self._bound: ContextVar[
            tuple[str, str, str | None, AgentPolicyProjection] | None
        ] = ContextVar(
            f"uv_agent_execution_policy_{id(self)}",
            default=None,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    @contextmanager
    def bind(
        self,
        *,
        project_id: str,
        action_id: str,
        model_id: str | None,
        policy: AgentPolicyProjection,
    ) -> Iterator[None]:
        token = self._bound.set((project_id, action_id, model_id, policy))
        try:
            yield
        finally:
            self._bound.reset(token)

    def policy(
        self,
        *,
        project_id: str,
        action_id: str,
        model_id: str | None = None,
    ) -> AgentPolicyProjection:
        bound = self._bound.get()
        if bound is not None:
            bound_project, bound_action, bound_model, bound_policy = bound
            if (
                project_id == bound_project
                and action_id == bound_action
                and model_id == bound_model
            ):
                return bound_policy
        return self._base.policy(
            project_id=project_id,
            action_id=action_id,
            model_id=model_id,
        )


class AgentTaskCoordinator(_EvidenceAgentTaskCoordinator):
    """Stage-16 coordinator with fail-closed, store-neutral recovery provenance."""

    def __init__(
        self,
        harness: Any,
        *,
        planner: Any | None = None,
        plan_store: Any | None = None,
        task_store: Any | None = None,
    ) -> None:
        current_catalog = harness.catalog
        if isinstance(current_catalog, _ExecutionPolicyCatalog):
            self._execution_policy_catalog = current_catalog
        else:
            self._execution_policy_catalog = _ExecutionPolicyCatalog(current_catalog)
            harness.catalog = self._execution_policy_catalog
        super().__init__(
            harness,
            planner=planner,
            plan_store=plan_store,
            task_store=task_store,
        )

    @staticmethod
    def _require_execution_reference_budget(plan: Any) -> None:
        if len(plan.canonical_references) > EXECUTION_SAFE_PLAN_REFERENCE_LIMIT:
            raise AgentTaskStateError(
                "durable Agent plan canonical references exceed the execution-safe "
                f"limit of {EXECUTION_SAFE_PLAN_REFERENCE_LIMIT}; dispatch refused"
            )

    def _recovered_success_trace(
        self,
        plan: Any,
        record: AgentTaskRecord,
        *,
        created_at: str,
        result_references: Mapping[str, str],
        extra_references: Sequence[str] = (),
        context_digest: str | None = None,
    ) -> AgentTraceRecord:
        self._require_execution_reference_budget(plan)
        spec = plan.task(record.task_id)
        evidence = self._execution_evidence.get(
            project_id=record.project_id,
            plan_id=plan.plan_id,
            task_id=record.task_id,
            skill_id=spec.skill_id,
        )
        effective_context = context_digest
        if evidence is not None and effective_context is None:
            # Generation recovery has no ProjectUnitOfWork context snapshot. Use the
            # pre-dispatch evidence directly so recovery does not depend on a specific
            # AgentTaskStore implementation having enriched RUNNING references.
            effective_context = evidence.context_digest

        # Plan canonical references are durable orchestration provenance. Preserve
        # them through every shared-executor recovery path instead of making later
        # orchestration layers re-wrap Stage-16 just to keep plan-level provenance.
        references = list(plan.canonical_references)
        references.extend(extra_references)
        if spec.target_shot_id is not None:
            references.append(spec.target_shot_id)
        if spec.action_id == "production.accept_take":
            take_id = spec.inputs.get("take_id")
            if not isinstance(take_id, str) or not take_id:
                raise AgentTaskStateError(
                    "durable accept_take task lost its Take identity"
                )
            try:
                shot_id = self.harness.production.state(record.project_id).take(take_id).shot_id
            except Exception as exc:
                raise AgentTaskStateError(
                    f"could not recover affected Shot for accepted Take {take_id!r}: {exc}"
                ) from exc
            references.append(shot_id)

        return super()._recovered_success_trace(
            plan,
            record,
            created_at=created_at,
            result_references=result_references,
            extra_references=tuple(dict.fromkeys(references)),
            context_digest=effective_context,
        )

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        with self.project_store._lock, self.tasks.records.project_lock(project_id):
            plan = self.plans.get(project_id, plan_id)
            # This check must happen before context/policy capture, RUNNING transition,
            # execution evidence, or dispatch. It also protects durable Plans created
            # by older/injected planners that predate the execution-safe Planner bound.
            self._require_execution_reference_budget(plan)
            spec = plan.task(task_id)
            record = self.tasks.get(project_id, plan.plan_id, spec.task_id)
            if record.status is AgentTaskStatus.PLANNED:
                raise AgentTaskBlocked(
                    f"Agent Task {spec.task_id!r} is blocked by unsatisfied dependencies"
                )
            if record.status is not AgentTaskStatus.READY:
                raise AgentTaskStateError(
                    f"Agent Task {spec.task_id!r} is not runnable from {record.status.value!r}"
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
            correlation_id = _typed_correlation_reference(
                plan.plan_id,
                spec.task_id,
                spec.skill_id,
            )
            try:
                snapshot = self.harness.context.build(
                    project_id,
                    shot_id=spec.target_shot_id,
                )
            except Exception:
                # Preserve the existing Stage-15 preparation-failure path. No dispatch
                # can occur when canonical context construction itself fails.
                with _execution_correlation(correlation_id):
                    return super().execute_task(
                        project_id=project_id,
                        plan_id=plan.plan_id,
                        task_id=spec.task_id,
                        runtime_inputs=runtime_inputs,
                    )

            expected_input_digest = self._expected_input_digest(spec)
            # Policy evidence is mandatory. If lookup fails, abort while the task is
            # still READY and before any canonical/cost-bearing dispatch can occur.
            policy = self._execution_policy(project_id, spec, payload)
            model_id = payload.get("model_id")
            normalized_model_id = model_id if isinstance(model_id, str) else None

            with (
                self._correlated_traces.correlate(
                    plan.plan_id,
                    spec.task_id,
                    spec.skill_id,
                    *plan.canonical_references,
                    expected_input_digest=expected_input_digest,
                ),
                _execution_correlation(correlation_id),
                _execution_context(snapshot.digest),
                self._execution_policy_catalog.bind(
                    project_id=project_id,
                    action_id=spec.action_id,
                    model_id=normalized_model_id,
                    policy=policy,
                ),
            ):
                running = self.tasks.transition(record, AgentTaskStatus.RUNNING)
                try:
                    self._execution_evidence.append(
                        project_id=project_id,
                        plan_id=plan.plan_id,
                        task_id=spec.task_id,
                        action_id=spec.action_id,
                        skill_id=spec.skill_id,
                        context_digest=snapshot.digest,
                        input_digest=expected_input_digest,
                        policy=policy,
                    )
                except Exception as exc:
                    self.tasks.transition(
                        running,
                        AgentTaskStatus.FAILED,
                        error=exc,
                    )
                    raise

                try:
                    result = self.harness.execute(
                        project_id=project_id,
                        action_id=spec.action_id,
                        inputs=payload,
                        target_shot_id=spec.target_shot_id,
                    )
                except Exception as exc:
                    trace = self._correlated_trace_for(plan, running)
                    if trace is not None:
                        if trace.status is AgentTraceStatus.SUCCEEDED:
                            self.tasks.transition(
                                running,
                                AgentTaskStatus.SUCCEEDED,
                                trace=trace,
                            )
                            self.tasks.promote_ready(plan)
                            raise
                        self.tasks.transition(
                            running,
                            AgentTaskStatus.FAILED,
                            trace=trace,
                            error=exc,
                        )
                        raise
                    recovered = self._committed_recovery_trace(plan, running)
                    if recovered is not None:
                        # The effect is already authoritative; leave RUNNING so reopen
                        # can append the missing success trace without replay.
                        raise
                    self.tasks.transition(
                        running,
                        AgentTaskStatus.FAILED,
                        error=exc,
                    )
                    raise

                trace = self._correlated_trace_for(plan, running)
                if trace is None:
                    error = AgentTaskStateError(
                        "AgentHarness execution completed without an inspectable Stage-15 trace"
                    )
                    recovered = self._committed_recovery_trace(plan, running)
                    if recovered is not None:
                        raise error
                    self.tasks.transition(
                        running,
                        AgentTaskStatus.FAILED,
                        error=error,
                    )
                    raise error

                self.tasks.transition(
                    running,
                    AgentTaskStatus.SUCCEEDED,
                    trace=trace,
                )
                self.tasks.promote_ready(plan)
                return result


__all__ = [
    "AgentPlanner",
    "AgentTaskCoordinator",
    "EXECUTION_SAFE_PLAN_REFERENCE_LIMIT",
]
