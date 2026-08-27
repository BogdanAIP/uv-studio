"""Stage-17 consistency refinements for bounded functional-subagent delegation."""

from __future__ import annotations

from typing import Any

from .models import safe_error_message, stable_digest
from .orchestration import AgentPlanRecord, AgentTaskStateError
from .subagents import (
    AgentSubagentCoordinator as _BaseAgentSubagentCoordinator,
    AgentSubagentContext,
    AgentSubagentError,
    AgentSubagentRequest,
    AgentSubagentResult,
)


class AgentSubagentCoordinator(_BaseAgentSubagentCoordinator):
    """Bind untrusted role output to one exact bounded role-context snapshot."""

    @staticmethod
    def _role_context_digest(context: AgentSubagentContext) -> str:
        return stable_digest(context.to_dict())

    def _critic_evidence(self, request: AgentSubagentRequest) -> dict[str, Any]:
        evidence = super()._critic_evidence(request)
        expected_trace_ids = {
            task["trace_id"]
            for task in evidence["tasks"]
            if task.get("trace_id") is not None
        }
        observed_trace_ids = {
            trace["trace_id"]
            for trace in evidence["traces"]
            if trace.get("trace_id") is not None
        }
        if observed_trace_ids != expected_trace_ids:
            missing = sorted(expected_trace_ids.difference(observed_trace_ids))
            unexpected = sorted(observed_trace_ids.difference(expected_trace_ids))
            raise AgentTaskStateError(
                "critic evidence does not match durable Agent Task trace references "
                f"(missing={missing!r}, unexpected={unexpected!r})"
            )
        return evidence

    def delegate(self, request: AgentSubagentRequest) -> AgentSubagentResult:
        context = self.prepare(request)
        context_digest = self._role_context_digest(context)
        try:
            raw = self.proposer.propose(context)
        except Exception as exc:
            raise AgentSubagentError(
                f"functional subagent proposer failed: {safe_error_message(exc)}"
            ) from exc

        current_context = self.prepare(request)
        if self._role_context_digest(current_context) != context_digest:
            raise AgentSubagentError(
                "functional subagent context changed during delegation; rebuild the role result"
            )

        summary, findings, proposals = self._parse_output(context, raw)
        self._validate_role_output(context.definition, proposals)

        validated_plan: AgentPlanRecord | None = None
        if proposals:
            validated_plan = self.planner.build(
                project_id=request.project_id,
                goal=request.objective,
                proposals=proposals,
                target_shot_id=request.target_shot_id,
                canonical_references=request.canonical_references,
            )
        return AgentSubagentResult(
            request=request,
            context_digest=context_digest,
            summary=summary,
            findings=findings,
            proposals=proposals,
            validated_plan=validated_plan,
        )

    def persist_plan(
        self,
        result: AgentSubagentResult,
        *,
        plan_id: str | None = None,
    ):
        if not isinstance(result, AgentSubagentResult):
            raise AgentSubagentError("persist_plan requires AgentSubagentResult")
        current_context = self.prepare(result.request)
        if self._role_context_digest(current_context) != result.context_digest:
            raise AgentSubagentError(
                "functional subagent context changed since delegation; delegate again before persisting"
            )
        return super().persist_plan(result, plan_id=plan_id)


__all__ = ["AgentSubagentCoordinator"]
