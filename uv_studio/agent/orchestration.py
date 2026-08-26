"""D-066 layer 2: bounded Planner, durable Agent Tasks and Skills."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from uv_studio.capabilities.models import CapabilityEffects
from uv_studio.projects.models import ProjectValidationError, utc_now_iso, validate_identifier
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore

from .harness import AgentActionCatalog, AgentHarness
from .models import (
    AgentHarnessError,
    AgentPolicyProjection,
    AgentPortableStateError,
    AgentTraceRecord,
    AgentUnknownAction,
    portable_json,
    safe_error_message,
    safe_text,
)

AGENT_PLAN_SCHEMA_VERSION = 1
AGENT_TASK_SCHEMA_VERSION = 1
AGENT_PLAN_RECORD_TYPE = "agent_plan"
AGENT_TASK_RECORD_TYPE = "agent_task"

_MAX_PLAN_STEPS = 32
_MAX_EXPANDED_TASKS = 64
_MAX_DEPENDENCIES = 32
_MAX_CANONICAL_REFERENCES = 128
_MAX_PAYLOAD_BYTES = 32 * 1024
_MAX_GOAL_LENGTH = 1200


class AgentPlanningError(AgentHarnessError):
    """A proposed plan cannot be represented by the bounded UV contract."""


class AgentSkillError(AgentPlanningError):
    """A Skill is unknown, invalid or cannot expand within the approved catalog."""


class AgentTaskStateError(AgentHarnessError):
    """A durable Agent Task transition or persisted record is invalid."""


class AgentTaskBlocked(AgentTaskStateError):
    """A task is not runnable because its dependencies have not succeeded."""


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise AgentPlanningError(str(exc)) from exc


def _identifier_tuple(
    values: Sequence[str],
    *,
    field_name: str,
    maximum: int,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise AgentPlanningError(f"{field_name} must be a sequence of identifiers")
    normalized = tuple(_identifier(value, field_name=field_name) for value in values)
    if len(normalized) > maximum:
        raise AgentPlanningError(f"{field_name} exceeds {maximum} items")
    if len(set(normalized)) != len(normalized):
        raise AgentPlanningError(f"{field_name} contains duplicate identifiers")
    return normalized


def _portable_payload(value: Mapping[str, Any], *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentPortableStateError(f"{field_name} must be a JSON object")
    normalized = portable_json(dict(value), field_name=field_name)
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > _MAX_PAYLOAD_BYTES:
        raise AgentPortableStateError(
            f"{field_name} exceeds {_MAX_PAYLOAD_BYTES} serialized bytes"
        )
    return normalized


def _sha256_hex(value: Any, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise AgentPlanningError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _effects_union(effects: Sequence[CapabilityEffects]) -> CapabilityEffects:
    fields = tuple(CapabilityEffects().to_dict())
    return CapabilityEffects(
        **{
            field_name: any(getattr(item, field_name) for item in effects)
            for field_name in fields
        }
    )


@dataclass(frozen=True)
class AgentPlanStepProposal:
    """Strict planner input. Exactly one action or Skill is selected per step."""

    step_id: str
    inputs: dict[str, Any]
    dependencies: tuple[str, ...] = ()
    action_id: str | None = None
    skill_id: str | None = None
    target_shot_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _identifier(self.step_id, field_name="step_id"))
        if (self.action_id is None) == (self.skill_id is None):
            raise AgentPlanningError("planner step must select exactly one action_id or skill_id")
        if self.action_id is not None:
            if not isinstance(self.action_id, str) or not self.action_id.strip():
                raise AgentPlanningError("action_id must be non-empty text")
            object.__setattr__(self, "action_id", self.action_id.strip())
        if self.skill_id is not None:
            object.__setattr__(
                self,
                "skill_id",
                _identifier(self.skill_id, field_name="skill_id"),
            )
        object.__setattr__(
            self,
            "dependencies",
            _identifier_tuple(
                self.dependencies,
                field_name="planner dependency",
                maximum=_MAX_DEPENDENCIES,
            ),
        )
        if self.step_id in self.dependencies:
            raise AgentPlanningError("planner step cannot depend on itself")
        if self.target_shot_id is not None:
            object.__setattr__(
                self,
                "target_shot_id",
                _identifier(self.target_shot_id, field_name="target_shot_id"),
            )
        object.__setattr__(
            self,
            "inputs",
            _portable_payload(self.inputs, field_name="planner step inputs"),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentPlanStepProposal":
        if not isinstance(data, Mapping):
            raise AgentPlanningError("planner step must be a JSON object")
        return cls(
            step_id=data["step_id"],
            action_id=data.get("action_id"),
            skill_id=data.get("skill_id"),
            inputs=dict(data.get("inputs", {})),
            dependencies=tuple(data.get("dependencies", ())),
            target_shot_id=data.get("target_shot_id"),
        )


@dataclass(frozen=True)
class AgentTaskSpec:
    """One concrete action-backed task in a validated Agent plan."""

    task_id: str
    action_id: str
    inputs: dict[str, Any]
    dependencies: tuple[str, ...]
    policy: AgentPolicyProjection
    target_shot_id: str | None = None
    skill_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _identifier(self.task_id, field_name="task_id"))
        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise AgentPlanningError("task action_id must be non-empty text")
        object.__setattr__(self, "action_id", self.action_id.strip())
        object.__setattr__(
            self,
            "inputs",
            _portable_payload(self.inputs, field_name="Agent Task inputs"),
        )
        object.__setattr__(
            self,
            "dependencies",
            _identifier_tuple(
                self.dependencies,
                field_name="task dependency",
                maximum=_MAX_DEPENDENCIES,
            ),
        )
        if self.task_id in self.dependencies:
            raise AgentPlanningError("Agent Task cannot depend on itself")
        if not isinstance(self.policy, AgentPolicyProjection):
            raise AgentPlanningError("task policy must be AgentPolicyProjection")
        if self.policy.action_id != self.action_id:
            raise AgentPlanningError("task policy action_id mismatch")
        if self.target_shot_id is not None:
            object.__setattr__(
                self,
                "target_shot_id",
                _identifier(self.target_shot_id, field_name="target_shot_id"),
            )
        if self.skill_id is not None:
            object.__setattr__(
                self,
                "skill_id",
                _identifier(self.skill_id, field_name="skill_id"),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "action_id": self.action_id,
            "skill_id": self.skill_id,
            "target_shot_id": self.target_shot_id,
            "dependencies": list(self.dependencies),
            "inputs": portable_json(self.inputs, field_name="Agent Task inputs"),
            "policy": self.policy.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentTaskSpec":
        if not isinstance(data, Mapping):
            raise AgentPlanningError("Agent Task spec must be a JSON object")
        try:
            return cls(
                task_id=data["task_id"],
                action_id=data["action_id"],
                skill_id=data.get("skill_id"),
                target_shot_id=data.get("target_shot_id"),
                dependencies=tuple(data.get("dependencies", ())),
                inputs=dict(data.get("inputs", {})),
                policy=AgentPolicyProjection.from_dict(data["policy"]),
            )
        except KeyError as exc:
            raise AgentPlanningError(f"missing Agent Task spec field: {exc.args[0]}") from exc


@dataclass(frozen=True)
class AgentPlanRecord:
    plan_id: str
    project_id: str
    context_digest: str
    goal: str
    canonical_references: tuple[str, ...]
    tasks: tuple[AgentTaskSpec, ...]
    created_at: str
    schema_version: int = AGENT_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_PLAN_SCHEMA_VERSION:
            raise AgentPlanningError(
                f"AgentPlanRecord only represents schema v{AGENT_PLAN_SCHEMA_VERSION}"
            )
        object.__setattr__(self, "plan_id", _identifier(self.plan_id, field_name="plan_id"))
        object.__setattr__(
            self,
            "project_id",
            _identifier(self.project_id, field_name="project_id"),
        )
        object.__setattr__(
            self,
            "context_digest",
            _sha256_hex(self.context_digest, field_name="context_digest"),
        )
        object.__setattr__(
            self,
            "goal",
            safe_text(self.goal, field_name="Agent plan goal", max_length=_MAX_GOAL_LENGTH),
        )
        refs = _identifier_tuple(
            self.canonical_references,
            field_name="plan canonical reference",
            maximum=_MAX_CANONICAL_REFERENCES,
        )
        object.__setattr__(self, "canonical_references", refs)
        tasks = tuple(self.tasks)
        if not tasks:
            raise AgentPlanningError("Agent plan requires at least one task")
        if len(tasks) > _MAX_EXPANDED_TASKS:
            raise AgentPlanningError(
                f"Agent plan exceeds {_MAX_EXPANDED_TASKS} concrete tasks"
            )
        if any(not isinstance(task, AgentTaskSpec) for task in tasks):
            raise AgentPlanningError("Agent plan tasks must contain AgentTaskSpec values")
        task_ids = tuple(task.task_id for task in tasks)
        if len(set(task_ids)) != len(task_ids):
            raise AgentPlanningError("Agent plan contains duplicate task identities")
        task_id_set = set(task_ids)
        for task in tasks:
            missing = set(task.dependencies).difference(task_id_set)
            if missing:
                raise AgentPlanningError(
                    f"task {task.task_id!r} references missing dependencies: {sorted(missing)!r}"
                )
        object.__setattr__(self, "tasks", tasks)
        self._validate_acyclic()
        if not isinstance(self.created_at, str) or not self.created_at:
            raise AgentPlanningError("Agent plan created_at is required")

    def _validate_acyclic(self) -> None:
        graph = {task.task_id: task.dependencies for task in self.tasks}
        state: dict[str, int] = {}

        def visit(task_id: str) -> None:
            marker = state.get(task_id, 0)
            if marker == 1:
                raise AgentPlanningError("Agent plan dependency graph contains a cycle")
            if marker == 2:
                return
            state[task_id] = 1
            for dependency in graph[task_id]:
                visit(dependency)
            state[task_id] = 2

        for task_id in graph:
            visit(task_id)

    def task(self, task_id: str) -> AgentTaskSpec:
        normalized = _identifier(task_id, field_name="task_id")
        for task in self.tasks:
            if task.task_id == normalized:
                return task
        raise AgentPlanningError(f"unknown task in plan {self.plan_id!r}: {normalized!r}")

    @property
    def topological_task_ids(self) -> tuple[str, ...]:
        ordered: list[str] = []
        visited: set[str] = set()
        by_id = {task.task_id: task for task in self.tasks}

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            for dependency in by_id[task_id].dependencies:
                visit(dependency)
            visited.add(task_id)
            ordered.append(task_id)

        for task in self.tasks:
            visit(task.task_id)
        return tuple(ordered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": AGENT_PLAN_RECORD_TYPE,
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "context_digest": self.context_digest,
            "goal": self.goal,
            "canonical_references": list(self.canonical_references),
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentPlanRecord":
        if not isinstance(data, Mapping) or data.get("record_type") != AGENT_PLAN_RECORD_TYPE:
            raise AgentPlanningError("task record is not an Agent plan")
        try:
            return cls(
                schema_version=data["schema_version"],
                plan_id=data["plan_id"],
                project_id=data["project_id"],
                context_digest=data["context_digest"],
                goal=data["goal"],
                canonical_references=tuple(data.get("canonical_references", ())),
                tasks=tuple(AgentTaskSpec.from_dict(item) for item in data["tasks"]),
                created_at=data["created_at"],
            )
        except KeyError as exc:
            raise AgentPlanningError(f"missing Agent plan field: {exc.args[0]}") from exc


@dataclass(frozen=True)
class AgentSkillDefinition:
    skill_id: str
    title: str
    description: str
    input_fields: tuple[str, ...]
    action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "skill_id", _identifier(self.skill_id, field_name="skill_id"))
        object.__setattr__(
            self,
            "title",
            safe_text(self.title, field_name="Skill title", max_length=200),
        )
        object.__setattr__(
            self,
            "description",
            safe_text(self.description, field_name="Skill description", max_length=1000),
        )
        fields = tuple(self.input_fields)
        if len(fields) != len(set(fields)) or any(not isinstance(item, str) or not item for item in fields):
            raise AgentSkillError("Skill input_fields must be unique non-empty strings")
        object.__setattr__(self, "input_fields", fields)
        actions = tuple(self.action_ids)
        if not actions or len(actions) != len(set(actions)):
            raise AgentSkillError("Skill action_ids must be a non-empty unique tuple")
        object.__setattr__(self, "action_ids", actions)


@dataclass(frozen=True)
class _ExpandedTask:
    task_id: str
    action_id: str
    inputs: dict[str, Any]
    dependencies: tuple[str, ...]
    skill_id: str
    target_shot_id: str | None = None


class AgentSkillCatalog:
    """Small built-in Skill catalog that can only expand into approved Agent actions."""

    SCENE_WITH_SHOT = "production.scene_with_shot"

    def __init__(self, action_catalog: AgentActionCatalog) -> None:
        self.action_catalog = action_catalog
        definitions = (
            AgentSkillDefinition(
                skill_id=self.SCENE_WITH_SHOT,
                title="Create production scene with shot",
                description=(
                    "Create one Scene and then one dependent Shot using the existing "
                    "ProductionSemanticService-backed Agent actions."
                ),
                input_fields=(
                    "scene_id",
                    "title",
                    "summary",
                    "shot_id",
                    "intent",
                    "reference_ids",
                ),
                action_ids=("production.create_scene", "production.create_shot"),
            ),
        )
        self._skills = {definition.skill_id: definition for definition in definitions}
        for definition in definitions:
            for action_id in definition.action_ids:
                try:
                    self.action_catalog.get(action_id)
                except AgentUnknownAction as exc:
                    raise AgentSkillError(
                        f"Skill {definition.skill_id!r} references unknown action {action_id!r}"
                    ) from exc

    def list(self) -> tuple[AgentSkillDefinition, ...]:
        return tuple(self._skills[key] for key in sorted(self._skills))

    def get(self, skill_id: str) -> AgentSkillDefinition:
        normalized = _identifier(skill_id, field_name="skill_id")
        try:
            return self._skills[normalized]
        except KeyError as exc:
            raise AgentSkillError(f"unknown Agent Skill: {normalized!r}") from exc

    def describe(self, skill_id: str) -> dict[str, Any]:
        definition = self.get(skill_id)
        actions = tuple(self.action_catalog.get(action_id) for action_id in definition.action_ids)
        effects = _effects_union(tuple(action.effects for action in actions))
        return {
            "skill_id": definition.skill_id,
            "title": definition.title,
            "description": definition.description,
            "input_fields": list(definition.input_fields),
            "action_ids": list(definition.action_ids),
            "effects": effects.to_dict(),
            "uses_job_manager": any(bool(action.uses_job_manager) for action in actions),
            "authorization_may_be_required": any(
                bool(action.authorization_may_be_required) for action in actions
            ),
            "authorities": [action.authority for action in actions],
        }

    def terminal_task_id(self, skill_id: str, step_id: str) -> str:
        self.get(skill_id)
        normalized_step = _identifier(step_id, field_name="step_id")
        if skill_id == self.SCENE_WITH_SHOT:
            return _identifier(f"{normalized_step}.shot", field_name="skill terminal task_id")
        raise AgentSkillError(f"Skill {skill_id!r} has no bounded expander")

    def expand(
        self,
        *,
        skill_id: str,
        step_id: str,
        inputs: Mapping[str, Any],
        dependencies: tuple[str, ...],
        target_shot_id: str | None,
    ) -> tuple[_ExpandedTask, ...]:
        definition = self.get(skill_id)
        payload = _portable_payload(inputs, field_name=f"Skill {skill_id} inputs")
        unknown = set(payload).difference(definition.input_fields)
        if unknown:
            raise AgentSkillError(
                f"Skill {skill_id!r} received unsupported inputs: {sorted(unknown)!r}"
            )
        if skill_id != self.SCENE_WITH_SHOT:
            raise AgentSkillError(f"Skill {skill_id!r} has no bounded expander")
        required = {"scene_id", "title", "shot_id", "intent"}
        missing = required.difference(payload)
        if missing:
            raise AgentSkillError(
                f"Skill {skill_id!r} is missing inputs: {sorted(missing)!r}"
            )
        scene_task_id = _identifier(f"{step_id}.scene", field_name="skill task_id")
        shot_task_id = _identifier(f"{step_id}.shot", field_name="skill task_id")
        scene_inputs: dict[str, Any] = {
            "scene_id": payload["scene_id"],
            "title": payload["title"],
        }
        if "summary" in payload:
            scene_inputs["summary"] = payload["summary"]
        shot_inputs: dict[str, Any] = {
            "shot_id": payload["shot_id"],
            "scene_id": payload["scene_id"],
            "intent": payload["intent"],
        }
        if "reference_ids" in payload:
            shot_inputs["reference_ids"] = payload["reference_ids"]
        # Creation cannot target the not-yet-existing Shot for context construction.
        if target_shot_id is not None:
            raise AgentSkillError(
                "production.scene_with_shot must use project context, not target_shot_id"
            )
        return (
            _ExpandedTask(
                task_id=scene_task_id,
                action_id="production.create_scene",
                inputs=scene_inputs,
                dependencies=dependencies,
                skill_id=definition.skill_id,
            ),
            _ExpandedTask(
                task_id=shot_task_id,
                action_id="production.create_shot",
                inputs=shot_inputs,
                dependencies=(scene_task_id,),
                skill_id=definition.skill_id,
            ),
        )


class AgentPlanner:
    """Deterministic validator/expander for externally proposed structured plans."""

    def __init__(self, harness: AgentHarness, skills: AgentSkillCatalog | None = None) -> None:
        self.harness = harness
        self.skills = skills or AgentSkillCatalog(harness.catalog)

    def _action_task(
        self,
        *,
        project_id: str,
        task_id: str,
        action_id: str,
        inputs: Mapping[str, Any],
        dependencies: tuple[str, ...],
        target_shot_id: str | None,
        skill_id: str | None,
    ) -> AgentTaskSpec:
        try:
            definition = self.harness.catalog.get(action_id)
        except AgentUnknownAction as exc:
            raise AgentPlanningError(f"unknown Agent action: {action_id!r}") from exc
        payload = _portable_payload(inputs, field_name=f"task {task_id} inputs")
        if "authorization_token" in payload:
            raise AgentPlanningError(
                "authorization_token is execution-only and must never be persisted in a plan"
            )
        unknown_fields = set(payload).difference(definition.input_fields)
        if unknown_fields:
            raise AgentPlanningError(
                f"action {action_id!r} received unsupported inputs: {sorted(unknown_fields)!r}"
            )
        model_id = payload.get("model_id")
        try:
            policy = self.harness.catalog.policy(
                project_id=project_id,
                action_id=action_id,
                model_id=model_id if isinstance(model_id, str) else None,
            )
        except Exception as exc:
            raise AgentPlanningError(
                f"could not resolve policy for action {action_id!r}: {safe_error_message(exc)}"
            ) from exc
        if not policy.available:
            raise AgentPlanningError(
                f"action {action_id!r} is unavailable: {policy.reason}"
            )
        return AgentTaskSpec(
            task_id=task_id,
            action_id=action_id,
            skill_id=skill_id,
            target_shot_id=target_shot_id,
            dependencies=dependencies,
            inputs=payload,
            policy=policy,
        )

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
        if isinstance(proposals, (str, bytes)):
            raise AgentPlanningError("planner proposals must be a sequence")
        proposal_items = tuple(proposals)
        if not proposal_items:
            raise AgentPlanningError("Planner requires at least one proposed step")
        if len(proposal_items) > _MAX_PLAN_STEPS:
            raise AgentPlanningError(f"Planner exceeds {_MAX_PLAN_STEPS} proposed steps")
        if any(not isinstance(item, AgentPlanStepProposal) for item in proposal_items):
            raise AgentPlanningError("planner proposals must contain AgentPlanStepProposal values")
        step_ids = tuple(item.step_id for item in proposal_items)
        if len(set(step_ids)) != len(step_ids):
            raise AgentPlanningError("Planner contains duplicate step identities")
        step_id_set = set(step_ids)
        for proposal in proposal_items:
            missing = set(proposal.dependencies).difference(step_id_set)
            if missing:
                raise AgentPlanningError(
                    f"step {proposal.step_id!r} references missing dependencies: {sorted(missing)!r}"
                )

        snapshot = self.harness.context.build(project_id, shot_id=target_shot_id)
        endpoints: dict[str, str] = {}
        for proposal in proposal_items:
            if proposal.action_id is not None:
                endpoints[proposal.step_id] = proposal.step_id
            else:
                assert proposal.skill_id is not None
                endpoints[proposal.step_id] = self.skills.terminal_task_id(
                    proposal.skill_id,
                    proposal.step_id,
                )

        tasks: list[AgentTaskSpec] = []
        for proposal in proposal_items:
            translated_dependencies = tuple(endpoints[item] for item in proposal.dependencies)
            effective_target = proposal.target_shot_id or target_shot_id
            if proposal.action_id is not None:
                tasks.append(
                    self._action_task(
                        project_id=project_id,
                        task_id=proposal.step_id,
                        action_id=proposal.action_id,
                        inputs=proposal.inputs,
                        dependencies=translated_dependencies,
                        target_shot_id=effective_target,
                        skill_id=None,
                    )
                )
                continue
            assert proposal.skill_id is not None
            expanded = self.skills.expand(
                skill_id=proposal.skill_id,
                step_id=proposal.step_id,
                inputs=proposal.inputs,
                dependencies=translated_dependencies,
                target_shot_id=effective_target,
            )
            for item in expanded:
                tasks.append(
                    self._action_task(
                        project_id=project_id,
                        task_id=item.task_id,
                        action_id=item.action_id,
                        inputs=item.inputs,
                        dependencies=item.dependencies,
                        target_shot_id=item.target_shot_id,
                        skill_id=item.skill_id,
                    )
                )

        if len(tasks) > _MAX_EXPANDED_TASKS:
            raise AgentPlanningError(
                f"expanded plan exceeds {_MAX_EXPANDED_TASKS} concrete tasks"
            )
        references = [snapshot.project_id, snapshot.target_id]
        references.extend(canonical_references)
        refs = _identifier_tuple(
            tuple(dict.fromkeys(references)),
            field_name="plan canonical reference",
            maximum=_MAX_CANONICAL_REFERENCES,
        )
        return AgentPlanRecord(
            plan_id=plan_id or f"agent_plan_{uuid.uuid4().hex}",
            project_id=project_id,
            context_digest=snapshot.digest,
            goal=goal,
            canonical_references=refs,
            tasks=tuple(tasks),
            created_at=utc_now_iso(),
        )


class AgentPlanStore:
    """Append-only durable plan descriptors in the existing project tasks/ root."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)

    def append(self, plan: AgentPlanRecord) -> Path:
        if not isinstance(plan, AgentPlanRecord):
            raise AgentPlanningError("AgentPlanStore.append requires AgentPlanRecord")
        with self.project_store._lock:
            self.project_store.load_project(plan.project_id)
            path = self.records.path(plan.project_id, plan.plan_id)
            if path.exists() or path.is_symlink():
                raise AgentPlanningError(f"Agent plan already exists: {plan.plan_id!r}")
            return self.records.write(plan.project_id, plan.plan_id, plan.to_dict())

    def get(self, project_id: str, plan_id: str) -> AgentPlanRecord:
        normalized = _identifier(plan_id, field_name="plan_id")
        with self.project_store._lock:
            path = self.records.path(project_id, normalized)
            if not path.is_file() or path.is_symlink():
                raise AgentPlanningError(f"Agent plan not found: {normalized!r}")
            try:
                plan = AgentPlanRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError, AgentHarnessError) as exc:
                raise AgentPlanningError(f"invalid Agent plan record {path.name!r}: {exc}") from exc
            if plan.project_id != project_id or plan.plan_id != normalized:
                raise AgentPlanningError("Agent plan record identity mismatch")
            return plan

    def list(self, project_id: str) -> tuple[AgentPlanRecord, ...]:
        with self.project_store._lock:
            project_dir = self.project_store.project_directory(project_id)
            plans: list[AgentPlanRecord] = []
            for path in sorted((project_dir / "tasks").glob("agent_plan_*.json")):
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    plan = AgentPlanRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, ValueError, json.JSONDecodeError, AgentHarnessError) as exc:
                    raise AgentPlanningError(f"invalid Agent plan record {path.name!r}: {exc}") from exc
                if plan.project_id != project_id or plan.plan_id != path.stem:
                    raise AgentPlanningError("Agent plan record identity mismatch")
                plans.append(plan)
            plans.sort(key=lambda item: (item.created_at, item.plan_id))
            return tuple(plans)


class AgentTaskStatus(str, Enum):
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentPlanStatus(str, Enum):
    ACTIVE = "active"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class AgentTaskRecord:
    record_id: str
    task_id: str
    plan_id: str
    project_id: str
    action_id: str
    status: AgentTaskStatus
    created_at: str
    updated_at: str
    skill_id: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    trace_id: str | None = None
    canonical_references: tuple[str, ...] = ()
    result_references: dict[str, str] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None
    schema_version: int = AGENT_TASK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_TASK_SCHEMA_VERSION:
            raise AgentTaskStateError(
                f"AgentTaskRecord only represents schema v{AGENT_TASK_SCHEMA_VERSION}"
            )
        for field_name in ("record_id", "task_id", "plan_id", "project_id"):
            try:
                object.__setattr__(
                    self,
                    field_name,
                    validate_identifier(getattr(self, field_name), field_name=field_name),
                )
            except ProjectValidationError as exc:
                raise AgentTaskStateError(str(exc)) from exc
        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise AgentTaskStateError("task action_id is required")
        object.__setattr__(self, "action_id", self.action_id.strip())
        if self.skill_id is not None:
            try:
                object.__setattr__(
                    self,
                    "skill_id",
                    validate_identifier(self.skill_id, field_name="skill_id"),
                )
            except ProjectValidationError as exc:
                raise AgentTaskStateError(str(exc)) from exc
        try:
            status = self.status if isinstance(self.status, AgentTaskStatus) else AgentTaskStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise AgentTaskStateError(f"invalid Agent Task status: {self.status!r}") from exc
        object.__setattr__(self, "status", status)
        for field_name in ("created_at", "updated_at"):
            if not isinstance(getattr(self, field_name), str) or not getattr(self, field_name):
                raise AgentTaskStateError(f"{field_name} is required")
        for field_name in ("started_at", "ended_at"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value):
                raise AgentTaskStateError(f"{field_name} must be non-empty text when present")
        if self.trace_id is not None:
            try:
                object.__setattr__(
                    self,
                    "trace_id",
                    validate_identifier(self.trace_id, field_name="trace_id"),
                )
            except ProjectValidationError as exc:
                raise AgentTaskStateError(str(exc)) from exc
        refs: list[str] = []
        try:
            for item in self.canonical_references:
                refs.append(validate_identifier(item, field_name="task canonical reference"))
        except ProjectValidationError as exc:
            raise AgentTaskStateError(str(exc)) from exc
        if len(refs) > _MAX_CANONICAL_REFERENCES or len(set(refs)) != len(refs):
            raise AgentTaskStateError("task canonical references are duplicate or unbounded")
        object.__setattr__(self, "canonical_references", tuple(refs))
        result_refs: dict[str, str] = {}
        if len(self.result_references) > 64:
            raise AgentTaskStateError("task result references exceed 64 entries")
        for key, value in self.result_references.items():
            if not isinstance(key, str) or not key.strip():
                raise AgentTaskStateError("task result reference keys must be non-empty text")
            try:
                result_refs[key.strip()] = validate_identifier(
                    value,
                    field_name=f"task result reference {key}",
                )
            except ProjectValidationError as exc:
                raise AgentTaskStateError(str(exc)) from exc
        object.__setattr__(self, "result_references", result_refs)

        if status in {AgentTaskStatus.PLANNED, AgentTaskStatus.READY}:
            if any(value is not None for value in (self.started_at, self.ended_at, self.trace_id)):
                raise AgentTaskStateError("planned/ready task cannot contain execution timestamps or trace")
            if self.error_type is not None or self.error_message is not None:
                raise AgentTaskStateError("planned/ready task cannot contain an error")
        elif status is AgentTaskStatus.RUNNING:
            if self.started_at is None or self.ended_at is not None:
                raise AgentTaskStateError("running task requires started_at and no ended_at")
            if self.error_type is not None or self.error_message is not None:
                raise AgentTaskStateError("running task cannot contain an error")
        elif status is AgentTaskStatus.SUCCEEDED:
            if self.started_at is None or self.ended_at is None or self.trace_id is None:
                raise AgentTaskStateError("succeeded task requires execution timestamps and trace_id")
            if self.error_type is not None or self.error_message is not None:
                raise AgentTaskStateError("succeeded task cannot contain an error")
        elif status is AgentTaskStatus.FAILED:
            if self.started_at is None or self.ended_at is None:
                raise AgentTaskStateError("failed task requires started_at and ended_at")
            if self.error_type is None or self.error_message is None:
                raise AgentTaskStateError("failed task requires error_type and error_message")
            object.__setattr__(
                self,
                "error_type",
                safe_text(self.error_type, field_name="task error_type", max_length=200),
            )
            object.__setattr__(
                self,
                "error_message",
                safe_text(self.error_message, field_name="task error_message", max_length=1000),
            )
        elif status is AgentTaskStatus.CANCELLED:
            if self.ended_at is None:
                raise AgentTaskStateError("cancelled task requires ended_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": AGENT_TASK_RECORD_TYPE,
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "action_id": self.action_id,
            "skill_id": self.skill_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "trace_id": self.trace_id,
            "canonical_references": list(self.canonical_references),
            "result_references": dict(self.result_references),
            "error_type": self.error_type,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentTaskRecord":
        if not isinstance(data, Mapping) or data.get("record_type") != AGENT_TASK_RECORD_TYPE:
            raise AgentTaskStateError("task record is not an Agent Task")
        try:
            return cls(
                schema_version=data["schema_version"],
                record_id=data["record_id"],
                task_id=data["task_id"],
                plan_id=data["plan_id"],
                project_id=data["project_id"],
                action_id=data["action_id"],
                skill_id=data.get("skill_id"),
                status=data["status"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                started_at=data.get("started_at"),
                ended_at=data.get("ended_at"),
                trace_id=data.get("trace_id"),
                canonical_references=tuple(data.get("canonical_references", ())),
                result_references=dict(data.get("result_references", {})),
                error_type=data.get("error_type"),
                error_message=data.get("error_message"),
            )
        except KeyError as exc:
            raise AgentTaskStateError(f"missing Agent Task field: {exc.args[0]}") from exc


class AgentTaskStore:
    """Mutable durable task state under the same project-scoped tasks/ authority."""

    _ALLOWED_TRANSITIONS = {
        AgentTaskStatus.PLANNED: {AgentTaskStatus.READY, AgentTaskStatus.CANCELLED},
        AgentTaskStatus.READY: {AgentTaskStatus.RUNNING, AgentTaskStatus.CANCELLED},
        AgentTaskStatus.RUNNING: {AgentTaskStatus.SUCCEEDED, AgentTaskStatus.FAILED},
        AgentTaskStatus.SUCCEEDED: set(),
        AgentTaskStatus.FAILED: set(),
        AgentTaskStatus.CANCELLED: set(),
    }

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.records = ProjectTaskRecordStore(project_store)

    def initialize(self, plan: AgentPlanRecord) -> tuple[AgentTaskRecord, ...]:
        with self.project_store._lock:
            if self.list_by_plan(plan.project_id, plan.plan_id):
                raise AgentTaskStateError(f"Agent Tasks already exist for plan {plan.plan_id!r}")
            now = utc_now_iso()
            result: list[AgentTaskRecord] = []
            for spec in plan.tasks:
                record = AgentTaskRecord(
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
                self.records.write(plan.project_id, record.record_id, record.to_dict())
                result.append(record)
            return tuple(result)

    def write(self, record: AgentTaskRecord) -> AgentTaskRecord:
        if not isinstance(record, AgentTaskRecord):
            raise AgentTaskStateError("AgentTaskStore.write requires AgentTaskRecord")
        with self.project_store._lock:
            self.project_store.load_project(record.project_id)
            self.records.write(record.project_id, record.record_id, record.to_dict())
            return record

    def list_by_plan(self, project_id: str, plan_id: str) -> tuple[AgentTaskRecord, ...]:
        normalized_plan = _identifier(plan_id, field_name="plan_id")
        with self.project_store._lock:
            project_dir = self.project_store.project_directory(project_id)
            tasks: list[AgentTaskRecord] = []
            for path in sorted((project_dir / "tasks").glob("agent_task_*.json")):
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    record = AgentTaskRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, ValueError, json.JSONDecodeError, AgentHarnessError) as exc:
                    raise AgentTaskStateError(f"invalid Agent Task record {path.name!r}: {exc}") from exc
                if record.project_id != project_id or record.record_id != path.stem:
                    raise AgentTaskStateError("Agent Task record identity mismatch")
                if record.plan_id == normalized_plan:
                    tasks.append(record)
            tasks.sort(key=lambda item: (item.created_at, item.task_id, item.record_id))
            return tuple(tasks)

    def get(self, project_id: str, plan_id: str, task_id: str) -> AgentTaskRecord:
        normalized_task = _identifier(task_id, field_name="task_id")
        matches = [
            record
            for record in self.list_by_plan(project_id, plan_id)
            if record.task_id == normalized_task
        ]
        if not matches:
            raise AgentTaskStateError(f"Agent Task not found: {normalized_task!r}")
        if len(matches) != 1:
            raise AgentTaskStateError(f"duplicate durable Agent Task identity: {normalized_task!r}")
        return matches[0]

    def transition(
        self,
        record: AgentTaskRecord,
        status: AgentTaskStatus,
        *,
        trace: AgentTraceRecord | None = None,
        error: Exception | None = None,
    ) -> AgentTaskRecord:
        target = status if isinstance(status, AgentTaskStatus) else AgentTaskStatus(status)
        allowed = self._ALLOWED_TRANSITIONS[record.status]
        if target not in allowed:
            raise AgentTaskStateError(
                f"invalid Agent Task transition: {record.status.value} -> {target.value}"
            )
        now = utc_now_iso()
        started_at = record.started_at
        ended_at = record.ended_at
        trace_id = record.trace_id
        canonical_references = record.canonical_references
        result_references = record.result_references
        error_type = record.error_type
        error_message = record.error_message
        if target is AgentTaskStatus.RUNNING:
            started_at = now
        elif target in {AgentTaskStatus.SUCCEEDED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED}:
            ended_at = now
        if trace is not None:
            trace_id = trace.trace_id
            canonical_references = trace.canonical_references
            result_references = dict(trace.result_references)
        if target is AgentTaskStatus.FAILED:
            if error is None:
                raise AgentTaskStateError("failed transition requires error")
            error_type = error.__class__.__name__
            error_message = safe_error_message(error)
        updated = replace(
            record,
            status=target,
            updated_at=now,
            started_at=started_at,
            ended_at=ended_at,
            trace_id=trace_id,
            canonical_references=canonical_references,
            result_references=result_references,
            error_type=error_type,
            error_message=error_message,
        )
        return self.write(updated)

    def promote_ready(self, plan: AgentPlanRecord) -> tuple[AgentTaskRecord, ...]:
        with self.project_store._lock:
            records = {record.task_id: record for record in self.list_by_plan(plan.project_id, plan.plan_id)}
            for spec in plan.tasks:
                record = records[spec.task_id]
                if record.status is not AgentTaskStatus.PLANNED:
                    continue
                if all(
                    records[dependency].status is AgentTaskStatus.SUCCEEDED
                    for dependency in spec.dependencies
                ):
                    records[spec.task_id] = self.transition(record, AgentTaskStatus.READY)
            return tuple(records[task_id] for task_id in plan.topological_task_ids)


@dataclass(frozen=True)
class AgentPlanExecutionState:
    plan: AgentPlanRecord
    tasks: tuple[AgentTaskRecord, ...]
    status: AgentPlanStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "status": self.status.value,
            "tasks": [task.to_dict() for task in self.tasks],
        }


class AgentTaskCoordinator:
    """Foreground dependency-aware executor over the existing AgentHarness authority."""

    def __init__(
        self,
        harness: AgentHarness,
        *,
        planner: AgentPlanner | None = None,
        plan_store: AgentPlanStore | None = None,
        task_store: AgentTaskStore | None = None,
    ) -> None:
        self.harness = harness
        self.project_store = harness.project_store
        self.planner = planner or AgentPlanner(harness)
        self.plans = plan_store or AgentPlanStore(self.project_store)
        self.tasks = task_store or AgentTaskStore(self.project_store)

    def create_plan(
        self,
        *,
        project_id: str,
        goal: str,
        proposals: Sequence[AgentPlanStepProposal],
        target_shot_id: str | None = None,
        canonical_references: Sequence[str] = (),
        plan_id: str | None = None,
    ) -> AgentPlanExecutionState:
        plan = self.planner.build(
            project_id=project_id,
            goal=goal,
            proposals=proposals,
            target_shot_id=target_shot_id,
            canonical_references=canonical_references,
            plan_id=plan_id,
        )
        with self.project_store._lock:
            self.plans.append(plan)
            self.tasks.initialize(plan)
        return self.state(project_id, plan.plan_id)

    @staticmethod
    def _plan_status(records: Sequence[AgentTaskRecord]) -> AgentPlanStatus:
        if records and all(record.status is AgentTaskStatus.SUCCEEDED for record in records):
            return AgentPlanStatus.SUCCEEDED
        if any(record.status is AgentTaskStatus.FAILED for record in records):
            return AgentPlanStatus.FAILED
        if records and all(record.status is AgentTaskStatus.CANCELLED for record in records):
            return AgentPlanStatus.CANCELLED
        if any(record.status is AgentTaskStatus.RUNNING for record in records):
            return AgentPlanStatus.RUNNING
        return AgentPlanStatus.ACTIVE

    def state(self, project_id: str, plan_id: str) -> AgentPlanExecutionState:
        plan = self.plans.get(project_id, plan_id)
        records_by_id = {
            record.task_id: record
            for record in self.tasks.list_by_plan(project_id, plan.plan_id)
        }
        if set(records_by_id) != {task.task_id for task in plan.tasks}:
            raise AgentTaskStateError("durable Agent Task set does not match the plan")
        records = tuple(records_by_id[task_id] for task_id in plan.topological_task_ids)
        return AgentPlanExecutionState(
            plan=plan,
            tasks=records,
            status=self._plan_status(records),
        )

    def runnable(self, project_id: str, plan_id: str) -> tuple[AgentTaskRecord, ...]:
        return tuple(
            record
            for record in self.state(project_id, plan_id).tasks
            if record.status is AgentTaskStatus.READY
        )

    def _trace_after(
        self,
        project_id: str,
        before_ids: set[str],
        action_id: str,
    ) -> AgentTraceRecord | None:
        candidates = [
            trace
            for trace in self.harness.traces.list(project_id)
            if trace.trace_id not in before_ids and trace.action_id == action_id
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.created_at, item.trace_id))
        return candidates[-1]

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

            payload = dict(spec.inputs)
            if runtime_inputs is not None:
                if not isinstance(runtime_inputs, Mapping):
                    raise AgentTaskStateError("runtime_inputs must be a mapping")
                unknown_runtime = set(runtime_inputs).difference({"authorization_token"})
                if unknown_runtime:
                    raise AgentTaskStateError(
                        f"unsupported execution-only inputs: {sorted(unknown_runtime)!r}"
                    )
                definition = self.harness.catalog.get(spec.action_id)
                if runtime_inputs and "authorization_token" not in definition.input_fields:
                    raise AgentTaskStateError(
                        f"action {spec.action_id!r} does not accept execution authorization"
                    )
                if "authorization_token" in runtime_inputs:
                    token = runtime_inputs["authorization_token"]
                    if token is not None and not isinstance(token, str):
                        raise AgentTaskStateError("authorization_token must be text or null")
                    payload["authorization_token"] = token

            running = self.tasks.transition(record, AgentTaskStatus.RUNNING)
            before_ids = {
                trace.trace_id for trace in self.harness.traces.list(project_id)
            }
            try:
                result = self.harness.execute(
                    project_id=project_id,
                    action_id=spec.action_id,
                    inputs=payload,
                    target_shot_id=spec.target_shot_id,
                )
            except Exception as exc:
                trace = self._trace_after(project_id, before_ids, spec.action_id)
                self.tasks.transition(
                    running,
                    AgentTaskStatus.FAILED,
                    trace=trace,
                    error=exc,
                )
                raise

            trace = self._trace_after(project_id, before_ids, spec.action_id)
            if trace is None:
                error = AgentTaskStateError(
                    "AgentHarness execution completed without an inspectable Stage-15 trace"
                )
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

    def cancel_task(self, *, project_id: str, plan_id: str, task_id: str) -> AgentTaskRecord:
        with self.project_store._lock:
            record = self.tasks.get(project_id, plan_id, task_id)
            if record.status not in {AgentTaskStatus.PLANNED, AgentTaskStatus.READY}:
                raise AgentTaskStateError(
                    f"Agent Task {task_id!r} cannot be cancelled from {record.status.value!r}"
                )
            return self.tasks.transition(record, AgentTaskStatus.CANCELLED)
