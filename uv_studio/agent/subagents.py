"""D-066 layer 3: bounded foreground functional subagents over existing Agent authorities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence

from uv_studio.projects.models import ProjectValidationError, validate_identifier

from .harness import AgentActionCatalog, AgentHarness, AgentTraceStore
from .models import (
    AgentActionDefinition,
    AgentContextSnapshot,
    AgentHarnessError,
    AgentPortableStateError,
    portable_json,
    safe_error_message,
    safe_text,
)
from .orchestration import (
    AgentPlanExecutionState,
    AgentPlanRecord,
    AgentPlanStepProposal,
    AgentTaskStateError,
)
from .stage16_generation_target import AgentPlanner, AgentTaskCoordinator, AgentTaskStore
from .stage16_runtime import AgentPlanStore

AGENT_SUBAGENT_SCHEMA_VERSION = 1

_MAX_FINDINGS = 16
_MAX_PROPOSALS = 32
_MAX_REFERENCES = 128
_MAX_OUTPUT_BYTES = 32 * 1024
_MAX_OBJECTIVE_LENGTH = 1200
_MAX_SUMMARY_LENGTH = 2000
_MAX_FINDING_LENGTH = 1200

_MEDIA_ACTION_IDS = frozenset(
    {
        "generation.submit",
        "production.register_take",
        "production.accept_take",
        "timeline.create_track",
        "timeline.add_clip",
        "timeline.move_clip",
        "timeline.trim_clip",
        "timeline.remove_clip",
    }
)


class AgentSubagentError(AgentHarnessError):
    """A functional-subagent request, proposal or role boundary is invalid."""


class AgentSubagentRole(str, Enum):
    EXPLORE = "explore"
    PLAN = "plan"
    MEDIA = "media"
    CRITIC = "critic"


class AgentSubagentFindingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise AgentSubagentError(str(exc)) from exc


def _identifiers(
    values: Sequence[str],
    *,
    field_name: str,
    maximum: int = _MAX_REFERENCES,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise AgentSubagentError(f"{field_name} must be a sequence of identifiers")
    result = tuple(_identifier(value, field_name=field_name) for value in values)
    if len(result) > maximum:
        raise AgentSubagentError(f"{field_name} exceeds {maximum} items")
    if len(set(result)) != len(result):
        raise AgentSubagentError(f"{field_name} contains duplicate identifiers")
    return result


def _bounded_output(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentSubagentError("functional subagent output must be a JSON object")
    normalized = portable_json(dict(value), field_name="functional subagent output")
    if not isinstance(normalized, dict):
        raise AgentSubagentError("functional subagent output must normalize to a JSON object")
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > _MAX_OUTPUT_BYTES:
        raise AgentSubagentError(
            f"functional subagent output exceeds {_MAX_OUTPUT_BYTES} serialized bytes"
        )
    return normalized


def _collect_identifiers(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            result.update(_collect_identifiers(item))
        return result
    if isinstance(value, (list, tuple)):
        for item in value:
            result.update(_collect_identifiers(item))
        return result
    if isinstance(value, str):
        try:
            result.add(validate_identifier(value, field_name="context reference"))
        except ProjectValidationError:
            pass
    return result


@dataclass(frozen=True)
class AgentSubagentRequest:
    role: AgentSubagentRole
    project_id: str
    objective: str
    target_shot_id: str | None = None
    plan_id: str | None = None
    canonical_references: tuple[str, ...] = ()
    schema_version: int = AGENT_SUBAGENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_SUBAGENT_SCHEMA_VERSION:
            raise AgentSubagentError(
                f"AgentSubagentRequest only represents schema v{AGENT_SUBAGENT_SCHEMA_VERSION}"
            )
        try:
            role = self.role if isinstance(self.role, AgentSubagentRole) else AgentSubagentRole(self.role)
        except (TypeError, ValueError) as exc:
            raise AgentSubagentError(f"unknown functional subagent role: {self.role!r}") from exc
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "project_id", _identifier(self.project_id, field_name="project_id"))
        object.__setattr__(
            self,
            "objective",
            safe_text(
                self.objective,
                field_name="functional subagent objective",
                max_length=_MAX_OBJECTIVE_LENGTH,
            ),
        )
        if self.target_shot_id is not None:
            object.__setattr__(
                self,
                "target_shot_id",
                _identifier(self.target_shot_id, field_name="target_shot_id"),
            )
        if self.plan_id is not None:
            object.__setattr__(self, "plan_id", _identifier(self.plan_id, field_name="plan_id"))
        object.__setattr__(
            self,
            "canonical_references",
            _identifiers(
                self.canonical_references,
                field_name="functional subagent canonical reference",
            ),
        )
        if role is AgentSubagentRole.CRITIC and self.plan_id is None:
            raise AgentSubagentError("critic role requires plan_id")
        if role is not AgentSubagentRole.CRITIC and self.plan_id is not None:
            raise AgentSubagentError("plan_id is only accepted by the critic role in this slice")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "role": self.role.value,
            "project_id": self.project_id,
            "objective": self.objective,
            "target_shot_id": self.target_shot_id,
            "plan_id": self.plan_id,
            "canonical_references": list(self.canonical_references),
        }


@dataclass(frozen=True)
class AgentSubagentFinding:
    finding_id: str
    severity: AgentSubagentFindingSeverity
    summary: str
    canonical_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding_id", _identifier(self.finding_id, field_name="finding_id"))
        try:
            severity = (
                self.severity
                if isinstance(self.severity, AgentSubagentFindingSeverity)
                else AgentSubagentFindingSeverity(self.severity)
            )
        except (TypeError, ValueError) as exc:
            raise AgentSubagentError(f"invalid finding severity: {self.severity!r}") from exc
        object.__setattr__(self, "severity", severity)
        object.__setattr__(
            self,
            "summary",
            safe_text(
                self.summary,
                field_name="functional subagent finding",
                max_length=_MAX_FINDING_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "canonical_references",
            _identifiers(
                self.canonical_references,
                field_name="finding canonical reference",
            ),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentSubagentFinding":
        if not isinstance(data, Mapping):
            raise AgentSubagentError("functional subagent finding must be a JSON object")
        allowed = {"finding_id", "severity", "summary", "canonical_references"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise AgentSubagentError(
                f"functional subagent finding has unsupported fields: {sorted(unknown)!r}"
            )
        try:
            return cls(
                finding_id=data["finding_id"],
                severity=data["severity"],
                summary=data["summary"],
                canonical_references=tuple(data.get("canonical_references", ())),
            )
        except KeyError as exc:
            raise AgentSubagentError(
                f"functional subagent finding is missing field: {exc.args[0]}"
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity.value,
            "summary": self.summary,
            "canonical_references": list(self.canonical_references),
        }


@dataclass(frozen=True)
class AgentSubagentDefinition:
    role: AgentSubagentRole
    purpose: str
    may_propose_plan: bool
    allowed_action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.role, AgentSubagentRole):
            raise AgentSubagentError("subagent definition role must be AgentSubagentRole")
        object.__setattr__(
            self,
            "purpose",
            safe_text(self.purpose, field_name="functional subagent purpose", max_length=500),
        )
        if not isinstance(self.may_propose_plan, bool):
            raise AgentSubagentError("may_propose_plan must be boolean")
        action_ids = tuple(self.allowed_action_ids)
        if any(not isinstance(item, str) or not item.strip() for item in action_ids):
            raise AgentSubagentError("allowed_action_ids must contain non-empty action IDs")
        if len(set(action_ids)) != len(action_ids):
            raise AgentSubagentError("allowed_action_ids must be unique")
        object.__setattr__(self, "allowed_action_ids", action_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "purpose": self.purpose,
            "may_propose_plan": self.may_propose_plan,
            "allowed_action_ids": list(self.allowed_action_ids),
        }


class AgentSubagentCatalog:
    """Fixed functional-role catalog derived from the existing Agent action catalog."""

    def __init__(self, actions: AgentActionCatalog) -> None:
        all_action_ids = tuple(item.action_id for item in actions.list())
        media_action_ids = tuple(
            action_id for action_id in all_action_ids if action_id in _MEDIA_ACTION_IDS
        )
        self._definitions = {
            AgentSubagentRole.EXPLORE: AgentSubagentDefinition(
                role=AgentSubagentRole.EXPLORE,
                purpose="Inspect bounded canonical Agent context and return referenced findings only.",
                may_propose_plan=False,
                allowed_action_ids=(),
            ),
            AgentSubagentRole.PLAN: AgentSubagentDefinition(
                role=AgentSubagentRole.PLAN,
                purpose="Propose bounded action/Skill steps that must pass the existing AgentPlanner.",
                may_propose_plan=True,
                allowed_action_ids=all_action_ids,
            ),
            AgentSubagentRole.MEDIA: AgentSubagentDefinition(
                role=AgentSubagentRole.MEDIA,
                purpose="Propose bounded media, generation, Take and Timeline work through approved Agent actions.",
                may_propose_plan=True,
                allowed_action_ids=media_action_ids,
            ),
            AgentSubagentRole.CRITIC: AgentSubagentDefinition(
                role=AgentSubagentRole.CRITIC,
                purpose="Inspect one durable Agent plan/task/trace set and return advisory findings only.",
                may_propose_plan=False,
                allowed_action_ids=(),
            ),
        }

    def list(self) -> tuple[AgentSubagentDefinition, ...]:
        return tuple(self._definitions[role] for role in AgentSubagentRole)

    def get(self, role: AgentSubagentRole | str) -> AgentSubagentDefinition:
        try:
            normalized = role if isinstance(role, AgentSubagentRole) else AgentSubagentRole(role)
            return self._definitions[normalized]
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentSubagentError(f"unknown functional subagent role: {role!r}") from exc


@dataclass(frozen=True)
class AgentSubagentContext:
    request: AgentSubagentRequest
    snapshot: AgentContextSnapshot
    definition: AgentSubagentDefinition
    actions: tuple[AgentActionDefinition, ...]
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "context": self.snapshot.to_dict(),
            "role": self.definition.to_dict(),
            "actions": [item.to_dict() for item in self.actions],
            "evidence": portable_json(self.evidence, field_name="functional subagent evidence"),
        }


class AgentSubagentProvider(Protocol):
    """Synchronous proposal-only seam; it receives no mutation or authorization authority."""

    def propose(self, context: AgentSubagentContext) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class AgentSubagentResult:
    request: AgentSubagentRequest
    context_digest: str
    summary: str
    findings: tuple[AgentSubagentFinding, ...]
    proposals: tuple[AgentPlanStepProposal, ...]
    validated_plan: AgentPlanRecord | None = None
    schema_version: int = AGENT_SUBAGENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request": self.request.to_dict(),
            "context_digest": self.context_digest,
            "summary": self.summary,
            "findings": [item.to_dict() for item in self.findings],
            "proposals": [
                {
                    "step_id": item.step_id,
                    "action_id": item.action_id,
                    "skill_id": item.skill_id,
                    "target_shot_id": item.target_shot_id,
                    "dependencies": list(item.dependencies),
                    "inputs": portable_json(item.inputs, field_name="functional subagent proposal"),
                }
                for item in self.proposals
            ],
            "validated_plan": (
                self.validated_plan.to_dict() if self.validated_plan is not None else None
            ),
        }


class AgentSubagentCoordinator:
    """Foreground proposal validator/delegator over Stage-15/16 Agent authorities."""

    def __init__(
        self,
        harness: AgentHarness,
        provider: AgentSubagentProvider,
        *,
        planner: AgentPlanner | None = None,
        task_coordinator: AgentTaskCoordinator | None = None,
    ) -> None:
        self.harness = harness
        self.provider = provider
        self.catalog = AgentSubagentCatalog(harness.catalog)
        self.planner = planner or AgentPlanner(harness)
        self._task_coordinator = task_coordinator
        self.plans = AgentPlanStore(harness.project_store)
        self.tasks = AgentTaskStore(harness.project_store)
        self.traces = AgentTraceStore(harness.project_store)

    def _critic_evidence(self, request: AgentSubagentRequest) -> dict[str, Any]:
        assert request.plan_id is not None
        plan = self.plans.get(request.project_id, request.plan_id)
        records = self.tasks.list_by_plan(request.project_id, request.plan_id)
        records_by_id = {record.task_id: record for record in records}
        expected_ids = {spec.task_id for spec in plan.tasks}
        if set(records_by_id) != expected_ids:
            raise AgentTaskStateError("durable Agent Task set does not match the critic plan")
        trace_ids = {
            record.trace_id for record in records if record.trace_id is not None
        }
        traces = tuple(
            trace
            for trace in self.traces.list(request.project_id)
            if trace.trace_id in trace_ids
        )
        return {
            "plan": {
                "plan_id": plan.plan_id,
                "project_id": plan.project_id,
                "goal": plan.goal,
                "context_digest": plan.context_digest,
                "canonical_references": list(plan.canonical_references),
                "created_at": plan.created_at,
            },
            "tasks": [
                {
                    "task_id": spec.task_id,
                    "action_id": spec.action_id,
                    "skill_id": spec.skill_id,
                    "dependencies": list(spec.dependencies),
                    "status": records_by_id[spec.task_id].status.value,
                    "trace_id": records_by_id[spec.task_id].trace_id,
                    "canonical_references": list(
                        records_by_id[spec.task_id].canonical_references
                    ),
                    "result_references": dict(
                        records_by_id[spec.task_id].result_references
                    ),
                    "error_type": records_by_id[spec.task_id].error_type,
                    "error_message": records_by_id[spec.task_id].error_message,
                }
                for spec in plan.tasks
            ],
            "traces": [trace.to_dict() for trace in traces],
        }

    def prepare(self, request: AgentSubagentRequest) -> AgentSubagentContext:
        if not isinstance(request, AgentSubagentRequest):
            raise AgentSubagentError("prepare requires AgentSubagentRequest")
        snapshot = self.harness.context.build(
            request.project_id,
            shot_id=request.target_shot_id,
        )
        definition = self.catalog.get(request.role)
        evidence = (
            self._critic_evidence(request)
            if request.role is AgentSubagentRole.CRITIC
            else {}
        )
        observed = _collect_identifiers(
            {
                "context": snapshot.to_dict(),
                "evidence": evidence,
            }
        )
        missing = set(request.canonical_references).difference(observed)
        if missing:
            raise AgentSubagentError(
                "functional subagent request references identities absent from bounded context: "
                f"{sorted(missing)!r}"
            )
        actions = tuple(
            self.harness.catalog.get(action_id)
            for action_id in definition.allowed_action_ids
        )
        return AgentSubagentContext(
            request=request,
            snapshot=snapshot,
            definition=definition,
            actions=actions,
            evidence=evidence,
        )

    @staticmethod
    def _proposal_from_dict(data: Mapping[str, Any]) -> AgentPlanStepProposal:
        if not isinstance(data, Mapping):
            raise AgentSubagentError("functional subagent proposal must be a JSON object")
        allowed = {
            "step_id",
            "action_id",
            "skill_id",
            "inputs",
            "dependencies",
            "target_shot_id",
        }
        unknown = set(data).difference(allowed)
        if unknown:
            raise AgentSubagentError(
                f"functional subagent proposal has unsupported fields: {sorted(unknown)!r}"
            )
        try:
            return AgentPlanStepProposal.from_dict(data)
        except (KeyError, TypeError, ValueError, AgentHarnessError) as exc:
            raise AgentSubagentError(
                f"invalid functional subagent proposal: {safe_error_message(exc)}"
            ) from exc

    def _parse_output(
        self,
        context: AgentSubagentContext,
        raw: Mapping[str, Any],
    ) -> tuple[str, tuple[AgentSubagentFinding, ...], tuple[AgentPlanStepProposal, ...]]:
        payload = _bounded_output(raw)
        allowed = {"summary", "findings", "proposals"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise AgentSubagentError(
                f"functional subagent output has unsupported fields: {sorted(unknown)!r}"
            )
        if "summary" not in payload:
            raise AgentSubagentError("functional subagent output requires summary")
        summary = safe_text(
            payload["summary"],
            field_name="functional subagent summary",
            max_length=_MAX_SUMMARY_LENGTH,
        )

        finding_items = payload.get("findings", [])
        if not isinstance(finding_items, list):
            raise AgentSubagentError("functional subagent findings must be a JSON array")
        if len(finding_items) > _MAX_FINDINGS:
            raise AgentSubagentError(
                f"functional subagent findings exceed {_MAX_FINDINGS} items"
            )
        findings = tuple(AgentSubagentFinding.from_dict(item) for item in finding_items)
        if len({item.finding_id for item in findings}) != len(findings):
            raise AgentSubagentError("functional subagent findings contain duplicate IDs")

        proposal_items = payload.get("proposals", [])
        if not isinstance(proposal_items, list):
            raise AgentSubagentError("functional subagent proposals must be a JSON array")
        if len(proposal_items) > _MAX_PROPOSALS:
            raise AgentSubagentError(
                f"functional subagent proposals exceed {_MAX_PROPOSALS} items"
            )
        proposals = tuple(self._proposal_from_dict(item) for item in proposal_items)

        observed = _collect_identifiers(context.to_dict())
        for finding in findings:
            missing = set(finding.canonical_references).difference(observed)
            if missing:
                raise AgentSubagentError(
                    f"finding {finding.finding_id!r} references identities absent from "
                    f"bounded subagent context: {sorted(missing)!r}"
                )
        return summary, findings, proposals

    @staticmethod
    def _validate_role_output(
        definition: AgentSubagentDefinition,
        proposals: tuple[AgentPlanStepProposal, ...],
    ) -> None:
        if not definition.may_propose_plan and proposals:
            raise AgentSubagentError(
                f"{definition.role.value} role is advisory and cannot propose executable work"
            )
        if definition.role is AgentSubagentRole.PLAN and not proposals:
            raise AgentSubagentError("plan role must propose at least one bounded step")
        if definition.role is AgentSubagentRole.MEDIA:
            for proposal in proposals:
                if proposal.skill_id is not None:
                    raise AgentSubagentError(
                        "media role cannot expand general Skills in this slice"
                    )
                if proposal.action_id not in definition.allowed_action_ids:
                    raise AgentSubagentError(
                        f"media role cannot propose action {proposal.action_id!r}"
                    )

    def delegate(self, request: AgentSubagentRequest) -> AgentSubagentResult:
        context = self.prepare(request)
        try:
            raw = self.provider.propose(context)
        except Exception as exc:
            raise AgentSubagentError(
                f"functional subagent provider failed: {safe_error_message(exc)}"
            ) from exc
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
            context_digest=context.snapshot.digest,
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
    ) -> AgentPlanExecutionState:
        if not isinstance(result, AgentSubagentResult):
            raise AgentSubagentError("persist_plan requires AgentSubagentResult")
        if result.request.role not in {AgentSubagentRole.PLAN, AgentSubagentRole.MEDIA}:
            raise AgentSubagentError("advisory functional subagent result cannot create a plan")
        if not result.proposals:
            raise AgentSubagentError("functional subagent result has no plan proposals")
        if self._task_coordinator is None:
            self._task_coordinator = AgentTaskCoordinator(
                self.harness,
                planner=self.planner,
            )
        return self._task_coordinator.create_plan(
            project_id=result.request.project_id,
            goal=result.request.objective,
            proposals=result.proposals,
            target_shot_id=result.request.target_shot_id,
            canonical_references=result.request.canonical_references,
            plan_id=plan_id,
        )


__all__ = [
    "AGENT_SUBAGENT_SCHEMA_VERSION",
    "AgentSubagentCatalog",
    "AgentSubagentContext",
    "AgentSubagentCoordinator",
    "AgentSubagentDefinition",
    "AgentSubagentError",
    "AgentSubagentFinding",
    "AgentSubagentFindingSeverity",
    "AgentSubagentProvider",
    "AgentSubagentRequest",
    "AgentSubagentResult",
    "AgentSubagentRole",
]
