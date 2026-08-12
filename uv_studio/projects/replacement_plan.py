"""Typed provider-neutral approval gate for targeted replacement preparation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .continuity_brief import (
    ContinuityBriefError,
    ContinuityBriefNotFound,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
)
from .models import ProjectValidationError, validate_identifier
from .store import ProjectStore, ProjectStoreError

REPLACEMENT_PLAN_SCHEMA_VERSION = 1
REPLACEMENT_PLAN_PATH = "timeline/replacement-plans.json"
MAX_PLAN_CHANGE_ITEMS = 32
MAX_PLAN_CHANGE_TEXT = 512
MAX_PLAN_GOAL_TEXT = 4000

REPLACEMENT_METHOD_CLASSES = frozenset(
    {"deterministic_edit", "prepared_asset", "generative_transform"}
)
REPLACEMENT_AUDIO_STRATEGIES = frozenset({"preserve_source", "replacement_audio"})
SAMPLE_POLICY_NOT_REQUIRED = "not_required"
SAMPLE_POLICY_REQUIRED = "required_before_full_generation"


class ReplacementPlanError(ProjectValidationError):
    """Invalid or stale approved replacement plan."""


class ReplacementPlanNotFound(ReplacementPlanError):
    pass


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise ReplacementPlanError(str(exc)) from exc


def _text(value: Any, *, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ReplacementPlanError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ReplacementPlanError(f"{field_name} must not be empty")
    if len(normalized) > max_length:
        raise ReplacementPlanError(
            f"{field_name} must be <= {max_length} characters"
        )
    return normalized


def _text_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ReplacementPlanError(f"{field_name} must be a list of strings")
    if len(value) > MAX_PLAN_CHANGE_ITEMS:
        raise ReplacementPlanError(
            f"{field_name} must contain at most {MAX_PLAN_CHANGE_ITEMS} items"
        )
    result = tuple(
        _text(item, field_name=field_name, max_length=MAX_PLAN_CHANGE_TEXT)
        for item in value
    )
    if len(result) != len(set(result)):
        raise ReplacementPlanError(f"{field_name} must not contain duplicates")
    return result


def _id_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ReplacementPlanError(f"{field_name} must be a list of identifiers")
    result = tuple(_identifier(item, field_name=field_name) for item in value)
    if len(result) != len(set(result)):
        raise ReplacementPlanError(f"{field_name} must not contain duplicates")
    return tuple(sorted(result))


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    if unknown:
        raise ReplacementPlanError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    missing = allowed.difference(data)
    if missing:
        raise ReplacementPlanError(f"{kind} is missing fields: {sorted(missing)!r}")


def _brief_sha256(brief: RangeContinuityBrief) -> str:
    payload = json.dumps(
        brief.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_sha256(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise ReplacementPlanError("brief_sha256 must be a lowercase SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ReplacementPlanError(
            "brief_sha256 must be a lowercase SHA-256 hex digest"
        ) from exc
    return value


def _sample_policy_for_method(method_class: str) -> str:
    if method_class == "generative_transform":
        return SAMPLE_POLICY_REQUIRED
    return SAMPLE_POLICY_NOT_REQUIRED


@dataclass(frozen=True)
class ReplacementPlanProposal:
    """User/coordinator approval input; target identity is inherited from Brief."""

    edit_id: str
    method_class: str
    goal: str
    required_changes: tuple[str, ...]
    allowed_changes: tuple[str, ...] = ()
    forbidden_changes: tuple[str, ...] = ()
    audio_strategy: str = "preserve_source"

    def __post_init__(self) -> None:
        object.__setattr__(self, "edit_id", _identifier(self.edit_id, field_name="edit_id"))
        if not isinstance(self.method_class, str) or self.method_class not in REPLACEMENT_METHOD_CLASSES:
            raise ReplacementPlanError(
                f"method_class must be one of {sorted(REPLACEMENT_METHOD_CLASSES)!r}"
            )
        object.__setattr__(
            self,
            "goal",
            _text(self.goal, field_name="goal", max_length=MAX_PLAN_GOAL_TEXT),
        )
        required = _text_tuple(self.required_changes, field_name="required_changes")
        if not required:
            raise ReplacementPlanError("required_changes must contain at least one item")
        allowed = _text_tuple(self.allowed_changes, field_name="allowed_changes")
        forbidden = _text_tuple(self.forbidden_changes, field_name="forbidden_changes")
        overlaps = {
            "required/allowed": set(required).intersection(allowed),
            "required/forbidden": set(required).intersection(forbidden),
            "allowed/forbidden": set(allowed).intersection(forbidden),
        }
        conflicts = {name: sorted(values) for name, values in overlaps.items() if values}
        if conflicts:
            raise ReplacementPlanError(
                f"change-scope lists must be disjoint: {conflicts!r}"
            )
        if not isinstance(self.audio_strategy, str) or self.audio_strategy not in REPLACEMENT_AUDIO_STRATEGIES:
            raise ReplacementPlanError(
                f"audio_strategy must be one of {sorted(REPLACEMENT_AUDIO_STRATEGIES)!r}"
            )
        object.__setattr__(self, "required_changes", required)
        object.__setattr__(self, "allowed_changes", allowed)
        object.__setattr__(self, "forbidden_changes", forbidden)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edit_id": self.edit_id,
            "method_class": self.method_class,
            "goal": self.goal,
            "required_changes": list(self.required_changes),
            "allowed_changes": list(self.allowed_changes),
            "forbidden_changes": list(self.forbidden_changes),
            "audio_strategy": self.audio_strategy,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementPlanProposal":
        if not isinstance(data, Mapping):
            raise ReplacementPlanError("replacement plan proposal must be an object")
        allowed = {
            "edit_id",
            "method_class",
            "goal",
            "required_changes",
            "allowed_changes",
            "forbidden_changes",
            "audio_strategy",
        }
        _strict_fields(data, allowed=allowed, kind="replacement plan proposal")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ReplacementPlan:
    """Canonical approved pre-replacement plan bound to one exact Brief revision."""

    edit_id: str
    source_path: str
    start_us: int
    end_us: int
    brief_sha256: str
    method_class: str
    goal: str
    required_changes: tuple[str, ...]
    allowed_changes: tuple[str, ...]
    forbidden_changes: tuple[str, ...]
    audio_strategy: str
    sample_policy: str
    constraint_ids: tuple[str, ...]
    review_target_ids: tuple[str, ...]
    schema_version: int = REPLACEMENT_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != REPLACEMENT_PLAN_SCHEMA_VERSION
        ):
            raise ReplacementPlanError(
                f"unsupported replacement plan schema: {self.schema_version!r}"
            )
        object.__setattr__(self, "edit_id", _identifier(self.edit_id, field_name="edit_id"))
        try:
            from .media_ranges import ProjectMediaRange

            target = ProjectMediaRange(
                source_path=self.source_path,
                start_us=self.start_us,
                end_us=self.end_us,
            )
        except ProjectValidationError as exc:
            raise ReplacementPlanError(str(exc)) from exc
        object.__setattr__(self, "source_path", target.source_path)
        object.__setattr__(self, "start_us", target.start_us)
        object.__setattr__(self, "end_us", target.end_us)
        object.__setattr__(self, "brief_sha256", _validate_sha256(self.brief_sha256))

        proposal = ReplacementPlanProposal(
            edit_id=self.edit_id,
            method_class=self.method_class,
            goal=self.goal,
            required_changes=self.required_changes,
            allowed_changes=self.allowed_changes,
            forbidden_changes=self.forbidden_changes,
            audio_strategy=self.audio_strategy,
        )
        object.__setattr__(self, "method_class", proposal.method_class)
        object.__setattr__(self, "goal", proposal.goal)
        object.__setattr__(self, "required_changes", proposal.required_changes)
        object.__setattr__(self, "allowed_changes", proposal.allowed_changes)
        object.__setattr__(self, "forbidden_changes", proposal.forbidden_changes)
        object.__setattr__(self, "audio_strategy", proposal.audio_strategy)

        expected_sample_policy = _sample_policy_for_method(self.method_class)
        if self.sample_policy != expected_sample_policy:
            raise ReplacementPlanError(
                f"sample_policy for {self.method_class!r} must be {expected_sample_policy!r}"
            )
        object.__setattr__(
            self,
            "constraint_ids",
            _id_tuple(self.constraint_ids, field_name="constraint_ids"),
        )
        object.__setattr__(
            self,
            "review_target_ids",
            _id_tuple(self.review_target_ids, field_name="review_target_ids"),
        )

    @property
    def target_identity(self) -> tuple[str, str, int, int]:
        return (self.edit_id, self.source_path, self.start_us, self.end_us)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "edit_id": self.edit_id,
            "source_path": self.source_path,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "brief_sha256": self.brief_sha256,
            "method_class": self.method_class,
            "goal": self.goal,
            "required_changes": list(self.required_changes),
            "allowed_changes": list(self.allowed_changes),
            "forbidden_changes": list(self.forbidden_changes),
            "audio_strategy": self.audio_strategy,
            "sample_policy": self.sample_policy,
            "constraint_ids": list(self.constraint_ids),
            "review_target_ids": list(self.review_target_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementPlan":
        if not isinstance(data, Mapping):
            raise ReplacementPlanError("replacement plan must be an object")
        allowed = {
            "schema_version",
            "edit_id",
            "source_path",
            "start_us",
            "end_us",
            "brief_sha256",
            "method_class",
            "goal",
            "required_changes",
            "allowed_changes",
            "forbidden_changes",
            "audio_strategy",
            "sample_policy",
            "constraint_ids",
            "review_target_ids",
        }
        _strict_fields(data, allowed=allowed, kind="replacement plan")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ReplacementPlanState:
    plans: tuple[ReplacementPlan, ...] = ()
    schema_version: int = REPLACEMENT_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != REPLACEMENT_PLAN_SCHEMA_VERSION
        ):
            raise ReplacementPlanError(
                f"unsupported replacement plan state schema: {self.schema_version!r}"
            )
        plans = tuple(self.plans)
        if not all(isinstance(plan, ReplacementPlan) for plan in plans):
            raise ReplacementPlanError("plans must contain ReplacementPlan values")
        ids = [plan.edit_id for plan in plans]
        if len(ids) != len(set(ids)):
            raise ReplacementPlanError("only one approved plan may exist per edit_id")
        object.__setattr__(self, "plans", tuple(sorted(plans, key=lambda plan: plan.edit_id)))

    def get(self, edit_id: str) -> ReplacementPlan:
        normalized = _identifier(edit_id, field_name="edit_id")
        for plan in self.plans:
            if plan.edit_id == normalized:
                return plan
        raise ReplacementPlanNotFound(normalized)

    def upsert(self, plan: ReplacementPlan) -> "ReplacementPlanState":
        if not isinstance(plan, ReplacementPlan):
            raise ReplacementPlanError("upsert requires ReplacementPlan")
        return ReplacementPlanState(
            plans=tuple(item for item in self.plans if item.edit_id != plan.edit_id) + (plan,)
        )

    def remove(self, edit_id: str) -> "ReplacementPlanState":
        normalized = _identifier(edit_id, field_name="edit_id")
        remaining = tuple(item for item in self.plans if item.edit_id != normalized)
        if len(remaining) == len(self.plans):
            raise ReplacementPlanNotFound(normalized)
        return ReplacementPlanState(plans=remaining)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plans": [plan.to_dict() for plan in self.plans],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementPlanState":
        if not isinstance(data, Mapping):
            raise ReplacementPlanError("replacement plan state must be an object")
        allowed = {"schema_version", "plans"}
        _strict_fields(data, allowed=allowed, kind="replacement plan state")
        if not isinstance(data["plans"], list):
            raise ReplacementPlanError("plans must be a list")
        return cls(
            schema_version=data["schema_version"],
            plans=tuple(ReplacementPlan.from_dict(item) for item in data["plans"]),
        )


class ReplacementPlanStore:
    """Atomic approved-plan persistence with current-Brief validation."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _state_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                REPLACEMENT_PLAN_PATH,
                must_exist=False,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise ReplacementPlanError(str(exc)) from exc

    def load(
        self,
        project_id: str,
        *,
        validate_current: bool = False,
    ) -> ReplacementPlanState:
        path = self._state_path(project_id)
        if not path.exists():
            return ReplacementPlanState()
        if not path.is_file() or path.is_symlink():
            raise ReplacementPlanError("replacement plan path must be a regular project file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReplacementPlanError("replacement plan state is malformed JSON") from exc
        except OSError as exc:
            raise ReplacementPlanError("replacement plan state could not be read") from exc
        state = ReplacementPlanState.from_dict(data)
        if validate_current:
            self._validate_state(project_id, state)
        return state

    def _write(self, project_id: str, state: ReplacementPlanState) -> ReplacementPlanState:
        self.project_store._atomic_write_json(self._state_path(project_id), state.to_dict())
        return state

    def approve(
        self,
        project_id: str,
        proposal: ReplacementPlanProposal,
    ) -> ReplacementPlanState:
        if not isinstance(proposal, ReplacementPlanProposal):
            raise ReplacementPlanError("approve requires ReplacementPlanProposal")
        with self.project_store._lock:
            current = self.load(project_id)
            brief = self._validated_brief(project_id, proposal.edit_id)
            plan = ReplacementPlan(
                edit_id=brief.edit_id,
                source_path=brief.source_path,
                start_us=brief.start_us,
                end_us=brief.end_us,
                brief_sha256=_brief_sha256(brief),
                method_class=proposal.method_class,
                goal=proposal.goal,
                required_changes=proposal.required_changes,
                allowed_changes=proposal.allowed_changes,
                forbidden_changes=proposal.forbidden_changes,
                audio_strategy=proposal.audio_strategy,
                sample_policy=_sample_policy_for_method(proposal.method_class),
                constraint_ids=tuple(item.constraint_id for item in brief.constraints),
                review_target_ids=tuple(item.target_id for item in brief.review_targets),
            )
            return self._write(project_id, current.upsert(plan))

    def remove(self, project_id: str, edit_id: str) -> ReplacementPlanState:
        with self.project_store._lock:
            current = self.load(project_id)
            return self._write(project_id, current.remove(edit_id))

    def validate_project(self, project_id: str) -> ReplacementPlanState:
        return self.load(project_id, validate_current=True)

    def _validated_brief(self, project_id: str, edit_id: str) -> RangeContinuityBrief:
        try:
            state = RangeContinuityBriefStore(self.project_store).validate_project(project_id)
            return state.get(edit_id)
        except (ContinuityBriefError, ContinuityBriefNotFound, ProjectStoreError) as exc:
            raise ReplacementPlanError(
                f"replacement plan requires a current valid RangeContinuityBrief: {exc}"
            ) from exc

    def _validate_plan(self, project_id: str, plan: ReplacementPlan) -> None:
        brief = self._validated_brief(project_id, plan.edit_id)
        brief_identity = (brief.edit_id, brief.source_path, brief.start_us, brief.end_us)
        if plan.target_identity != brief_identity:
            raise ReplacementPlanError(
                f"replacement plan target for {plan.edit_id!r} no longer matches its Brief"
            )
        current_digest = _brief_sha256(brief)
        if plan.brief_sha256 != current_digest:
            raise ReplacementPlanError(
                f"replacement plan for {plan.edit_id!r} is stale because its Brief changed"
            )
        expected_constraints = tuple(sorted(item.constraint_id for item in brief.constraints))
        expected_reviews = tuple(sorted(item.target_id for item in brief.review_targets))
        if plan.constraint_ids != expected_constraints:
            raise ReplacementPlanError(
                f"replacement plan for {plan.edit_id!r} does not carry the current Brief constraints"
            )
        if plan.review_target_ids != expected_reviews:
            raise ReplacementPlanError(
                f"replacement plan for {plan.edit_id!r} does not carry the current Brief review targets"
            )

    def _validate_state(self, project_id: str, state: ReplacementPlanState) -> None:
        for plan in state.plans:
            self._validate_plan(project_id, plan)
