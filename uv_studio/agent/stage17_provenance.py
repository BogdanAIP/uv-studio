"""Stage-17 durable functional-subagent provenance over existing Agent authorities.

This layer keeps delegation foreground-only and does not add a subagent state store.
A validated delegation receives one typed, content-addressed Agent reference. When
plan/media output is accepted, that reference is carried by the durable Stage-16
Plan and, during execution, by the existing Stage-15 trace correlation path.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Any, Iterator, Mapping, Sequence

from .models import AgentHarnessError, AgentTraceRecord, safe_error_message, stable_digest
from .orchestration import (
    AgentPlanExecutionState,
    AgentPlanRecord,
    AgentTaskRecord,
    AgentTaskStateError,
    AgentTaskStatus,
)
from .stage16_generation_target import AgentTaskCoordinator as _Stage16AgentTaskCoordinator
from .stage17_consistency import AgentSubagentCoordinator as _ConsistencyAgentSubagentCoordinator
from .subagents import (
    AGENT_SUBAGENT_SCHEMA_VERSION,
    AgentSubagentContext,
    AgentSubagentError,
    AgentSubagentRequest,
    AgentSubagentResult as _BaseAgentSubagentResult,
    AgentSubagentRole,
)

_DELEGATION_REFERENCE_PREFIX = "agent_delegate_"
_DELEGATION_REFERENCE_PATTERN = re.compile(
    r"^agent_delegate_(?:explore|plan|media|critic)_[0-9a-f]{32}$"
)
_DELEGATION_BINDING_REFERENCE_PREFIX = "agent_delegate_bind_"

# Canonical identities that can be selected by current bounded Agent proposals.
# Server-generated identities are outside this map because callers cannot choose
# them. Keep Skills explicit so validation covers their expanded canonical outputs
# before any durable Plan or canonical mutation exists.
_RESERVED_ACTION_OUTPUT_FIELDS: dict[str, tuple[str, ...]] = {
    "production.create_scene": ("scene_id",),
    "production.create_shot": ("shot_id",),
    "production.register_take": ("take_id",),
    "production.accept_take": ("track_id", "clip_id"),
    "timeline.create_track": ("track_id",),
    "timeline.add_clip": ("clip_id",),
}
_RESERVED_SKILL_OUTPUT_FIELDS: dict[str, tuple[str, ...]] = {
    "production.scene_with_shot": ("scene_id", "shot_id"),
}


def _is_delegation_reference(value: Any) -> bool:
    return (
        isinstance(value, str)
        and _DELEGATION_REFERENCE_PATTERN.fullmatch(value) is not None
    )


def _delegation_binding_reference(
    *,
    project_id: str,
    goal: str,
    delegation_id: str,
) -> str:
    """Bind one delegation identity to the immutable durable Plan purpose.

    The binding is deliberately content-addressed rather than secret/authenticated:
    delegation provenance is inspection evidence, not an authorization token. Its
    purpose is to distinguish Stage-17-persisted provenance from arbitrary canonical
    identities that happen to match the delegation-ID syntax.
    """

    digest = stable_digest(
        {
            "record_type": "agent_subagent_plan_binding",
            "schema_version": AGENT_SUBAGENT_SCHEMA_VERSION,
            "project_id": project_id,
            "goal": goal,
            "delegation_id": delegation_id,
        }
    )
    return f"{_DELEGATION_BINDING_REFERENCE_PREFIX}{digest[:32]}"


def _validate_reserved_proposal_outputs(proposals: Sequence[Any]) -> None:
    for proposal in proposals:
        if proposal.action_id is not None:
            fields = _RESERVED_ACTION_OUTPUT_FIELDS.get(proposal.action_id, ())
        else:
            fields = _RESERVED_SKILL_OUTPUT_FIELDS.get(proposal.skill_id or "", ())
        for field_name in fields:
            value = proposal.inputs.get(field_name)
            if _is_delegation_reference(value):
                raise AgentSubagentError(
                    "planned canonical output collides with the reserved "
                    "functional-subagent delegation namespace: "
                    f"{field_name}={value!r}"
                )


def _proposal_payload(result: _BaseAgentSubagentResult) -> list[dict[str, Any]]:
    return [
        {
            "step_id": item.step_id,
            "action_id": item.action_id,
            "skill_id": item.skill_id,
            "target_shot_id": item.target_shot_id,
            "dependencies": list(item.dependencies),
            "inputs": item.inputs,
        }
        for item in result.proposals
    ]


def _delegation_id(result: _BaseAgentSubagentResult) -> str:
    digest = stable_digest(
        {
            "record_type": "agent_subagent_delegation",
            "schema_version": AGENT_SUBAGENT_SCHEMA_VERSION,
            "request": result.request.to_dict(),
            "context_digest": result.context_digest,
            "summary": result.summary,
            "findings": [item.to_dict() for item in result.findings],
            "proposals": _proposal_payload(result),
        }
    )
    return f"{_DELEGATION_REFERENCE_PREFIX}{result.request.role.value}_{digest[:32]}"


@dataclass(frozen=True)
class AgentSubagentResult(_BaseAgentSubagentResult):
    """Validated role result with a typed inspectable delegation identity."""

    delegation_id: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_SUBAGENT_SCHEMA_VERSION:
            raise AgentSubagentError(
                f"AgentSubagentResult only represents schema v{AGENT_SUBAGENT_SCHEMA_VERSION}"
            )
        if not isinstance(self.request, AgentSubagentRequest):
            raise AgentSubagentError("functional subagent result request is invalid")
        expected = _delegation_id(self)
        if self.delegation_id != expected:
            raise AgentSubagentError(
                "functional subagent delegation_id does not match validated result content"
            )

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["delegation_id"] = self.delegation_id
        return result


class _DelegationTraceStore:
    """Add one typed delegation reference before the existing trace store appends."""

    def __init__(self, base: Any) -> None:
        self._base = base
        self._delegation_references: ContextVar[tuple[str, ...]] = ContextVar(
            f"uv_agent_delegation_trace_{id(self)}",
            default=(),
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    @staticmethod
    def with_references(
        record: AgentTraceRecord,
        references: tuple[str, ...],
    ) -> AgentTraceRecord:
        if not references:
            return record
        canonical_references = tuple(
            dict.fromkeys((*record.canonical_references, *references))
        )
        if canonical_references == record.canonical_references:
            return record
        return replace(record, canonical_references=canonical_references)

    @contextmanager
    def bind(self, *references: str) -> Iterator[None]:
        normalized = tuple(
            dict.fromkeys(
                item for item in references if _is_delegation_reference(item)
            )
        )
        token = self._delegation_references.set(normalized)
        try:
            yield
        finally:
            self._delegation_references.reset(token)

    def append(self, record: AgentTraceRecord):
        record = self.with_references(record, self._delegation_references.get())
        return self._base.append(record)

    def list(self, project_id: str):
        return self._base.list(project_id)


class AgentSubagentTaskCoordinator(_Stage16AgentTaskCoordinator):
    """Stage-16 foreground executor with Stage-17 delegation trace provenance."""

    def __init__(self, harness: Any, **kwargs: Any) -> None:
        current = harness.traces
        delegation_store: _DelegationTraceStore | None = None
        candidate = current
        for _ in range(4):
            if isinstance(candidate, _DelegationTraceStore):
                delegation_store = candidate
                break
            candidate = getattr(candidate, "_base", None)
            if candidate is None:
                break
        if delegation_store is None:
            delegation_store = _DelegationTraceStore(current)
            harness.traces = delegation_store
        self._delegation_traces = delegation_store
        super().__init__(harness, **kwargs)

    @staticmethod
    def _delegation_references(plan: Any) -> tuple[str, ...]:
        candidates = tuple(
            item
            for item in plan.canonical_references
            if _is_delegation_reference(item)
        )
        references = tuple(
            item
            for item in candidates
            if _delegation_binding_reference(
                project_id=plan.project_id,
                goal=plan.goal,
                delegation_id=item,
            )
            in plan.canonical_references
        )
        if len(references) > 1:
            raise AgentTaskStateError(
                "durable Agent plan contains multiple bound functional-subagent delegation references"
            )
        return references

    def _reconcile_running(
        self,
        plan: AgentPlanRecord,
        record: AgentTaskRecord,
    ) -> AgentTaskRecord:
        references = self._delegation_references(plan)

        trace = self._correlated_trace_for(plan, record)
        if trace is not None:
            return super()._reconcile_running(plan, record)

        recovered = self._transaction_recovery_trace(plan, record)
        if recovered is None:
            recovered = self._generation_recovery_trace(plan, record)
        if recovered is not None:
            enriched = self._delegation_traces.with_references(recovered, references)
            # Stage 16 intentionally validates that the trace supplied to the terminal
            # task transition is byte-for-byte the same durable Stage-15 trace record.
            # Append and transition with this exact enriched object rather than asking
            # the trace proxy to enrich a different local recovery object on append.
            self.harness.traces.append(enriched)
            return self.tasks.transition(
                record,
                AgentTaskStatus.SUCCEEDED,
                trace=enriched,
            )

        return super()._reconcile_running(plan, record)

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        plan = self.plans.get(project_id, plan_id)
        references = self._delegation_references(plan)
        with self._delegation_traces.bind(*references):
            return super().execute_task(
                project_id=project_id,
                plan_id=plan_id,
                task_id=task_id,
                runtime_inputs=runtime_inputs,
            )


class AgentSubagentCoordinator(_ConsistencyAgentSubagentCoordinator):
    """Bind accepted role output to durable Plan/Task/Trace provenance."""

    def __init__(self, harness: Any, proposer: Any, **kwargs: Any) -> None:
        task_coordinator = kwargs.get("task_coordinator")
        requested_planner = kwargs.get("planner")
        if requested_planner is not None and getattr(requested_planner, "harness", None) is not harness:
            raise AgentSubagentError(
                "Stage 17 planner must share the exact AgentHarness authority"
            )
        if task_coordinator is not None:
            if not isinstance(task_coordinator, AgentSubagentTaskCoordinator):
                raise AgentSubagentError(
                    "Stage 17 task_coordinator must preserve functional-subagent delegation provenance"
                )
            if (
                task_coordinator.harness is not harness
                or task_coordinator.project_store is not harness.project_store
                or getattr(task_coordinator.plans, "project_store", None)
                is not harness.project_store
                or getattr(task_coordinator.tasks, "project_store", None)
                is not harness.project_store
            ):
                raise AgentSubagentError(
                    "Stage 17 task_coordinator must share the exact AgentHarness and Project Store authority"
                )
            coordinator_planner = task_coordinator.planner
            if getattr(coordinator_planner, "harness", None) is not harness:
                raise AgentSubagentError(
                    "Stage 17 task_coordinator planner must share the exact AgentHarness authority"
                )
            if requested_planner is not None and coordinator_planner is not requested_planner:
                raise AgentSubagentError(
                    "Stage 17 task_coordinator must share the exact AgentPlanner authority"
                )
            if requested_planner is None:
                kwargs["planner"] = coordinator_planner
        super().__init__(harness, proposer, **kwargs)
        if task_coordinator is None:
            self._task_coordinator = AgentSubagentTaskCoordinator(
                harness,
                planner=self.planner,
            )

    def prepare(self, request: AgentSubagentRequest) -> AgentSubagentContext:
        context = super().prepare(request)
        if request.role is not AgentSubagentRole.CRITIC:
            collisions = tuple(
                reference
                for reference in context.available_references
                if _is_delegation_reference(reference)
            )
            if collisions:
                raise AgentSubagentError(
                    "canonical identity collides with the reserved functional-subagent delegation namespace: "
                    f"{sorted(collisions)!r}"
                )
        return context

    def delegate(self, request: AgentSubagentRequest) -> AgentSubagentResult:
        try:
            base = super().delegate(request)
        except AgentSubagentError:
            raise
        except AgentHarnessError as exc:
            raise AgentSubagentError(
                f"invalid functional subagent output: {safe_error_message(exc)}"
            ) from exc
        _validate_reserved_proposal_outputs(base.proposals)
        delegation_id = _delegation_id(base)
        binding_reference = _delegation_binding_reference(
            project_id=base.request.project_id,
            goal=base.request.objective,
            delegation_id=delegation_id,
        )
        validated_plan = base.validated_plan
        if validated_plan is not None:
            validated_plan = replace(
                validated_plan,
                canonical_references=tuple(
                    dict.fromkeys(
                        (
                            *validated_plan.canonical_references,
                            delegation_id,
                            binding_reference,
                        )
                    )
                ),
            )
        return AgentSubagentResult(
            request=base.request,
            context_digest=base.context_digest,
            summary=base.summary,
            findings=base.findings,
            proposals=base.proposals,
            validated_plan=validated_plan,
            schema_version=base.schema_version,
            delegation_id=delegation_id,
        )

    def persist_plan(
        self,
        result: _BaseAgentSubagentResult,
        *,
        plan_id: str | None = None,
    ) -> AgentPlanExecutionState:
        if not isinstance(result, AgentSubagentResult):
            raise AgentSubagentError(
                "persist_plan requires a validated Stage-17 AgentSubagentResult"
            )
        if result.request.role not in {AgentSubagentRole.PLAN, AgentSubagentRole.MEDIA}:
            raise AgentSubagentError("advisory functional subagent result cannot create a plan")
        if not result.proposals:
            raise AgentSubagentError("functional subagent result has no plan proposals")

        # Revalidate both the role envelope and reserved canonical-output namespace at
        # the persistence boundary. A frozen result can still be reconstructed by an
        # in-process caller; content-addressed provenance is not authorization.
        self._validate_role_output(
            self.catalog.get(result.request.role),
            tuple(result.proposals),
        )
        _validate_reserved_proposal_outputs(result.proposals)
        expected_delegation_id = _delegation_id(result)
        if result.delegation_id != expected_delegation_id:
            raise AgentSubagentError(
                "functional subagent delegation_id does not match validated result content"
            )

        current_context = self.prepare(result.request)
        if self._role_context_digest(current_context) != result.context_digest:
            raise AgentSubagentError(
                "functional subagent context changed since delegation; delegate again before persisting"
            )

        binding_reference = _delegation_binding_reference(
            project_id=result.request.project_id,
            goal=result.request.objective,
            delegation_id=result.delegation_id,
        )
        references = tuple(
            dict.fromkeys(
                (
                    *result.request.canonical_references,
                    result.delegation_id,
                    binding_reference,
                )
            )
        )
        if self._task_coordinator is None:
            self._task_coordinator = AgentSubagentTaskCoordinator(
                self.harness,
                planner=self.planner,
            )
        return self._task_coordinator.create_plan(
            project_id=result.request.project_id,
            goal=result.request.objective,
            proposals=result.proposals,
            target_shot_id=result.request.target_shot_id,
            canonical_references=references,
            plan_id=plan_id,
        )

    def execute_task(
        self,
        *,
        project_id: str,
        plan_id: str,
        task_id: str,
        runtime_inputs: Mapping[str, Any] | None = None,
    ) -> Any:
        if self._task_coordinator is None:
            self._task_coordinator = AgentSubagentTaskCoordinator(
                self.harness,
                planner=self.planner,
            )
        return self._task_coordinator.execute_task(
            project_id=project_id,
            plan_id=plan_id,
            task_id=task_id,
            runtime_inputs=runtime_inputs,
        )


__all__ = [
    "AgentSubagentCoordinator",
    "AgentSubagentResult",
    "AgentSubagentTaskCoordinator",
]
