"""Typed provider-neutral bounded continuity evidence for accepted range edits."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .edit_state import AcceptedRangeEdit, RangeEditStateStore
from .media_ranges import ProjectMediaRange
from .models import (
    ProjectValidationError,
    validate_identifier,
    validate_project_relative_path,
)
from .store import ProjectStore, ProjectStoreError

CONTINUITY_BRIEF_SCHEMA_VERSION = 1
CONTINUITY_BRIEF_PATH = "timeline/range-continuity-briefs.json"
MAX_CONTINUITY_EVIDENCE_SPAN_US = 30_000_000
_EVIDENCE_ROOTS = ("sources", "assets", "artifacts", "exports")
_EVIDENCE_ROLES = frozenset({"before", "requested", "after", "reference"})
_OBSERVATION_KINDS = frozenset({"observation", "inference"})
_CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
_CONSTRAINT_CATEGORIES = frozenset(
    {"visual", "motion", "audio", "timing", "content", "technical", "style"}
)


class ContinuityBriefError(ProjectValidationError):
    """Invalid or inconsistent RangeContinuityBrief state."""


class ContinuityBriefNotFound(ContinuityBriefError):
    pass


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise ContinuityBriefError(str(exc)) from exc


def _path(value: Any, *, field_name: str) -> str:
    try:
        return validate_project_relative_path(value)
    except ProjectValidationError as exc:
        raise ContinuityBriefError(f"{field_name}: {exc}") from exc


def _text(value: Any, *, field_name: str, max_length: int = 4000) -> str:
    if not isinstance(value, str):
        raise ContinuityBriefError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ContinuityBriefError(f"{field_name} must not be empty")
    if len(normalized) > max_length:
        raise ContinuityBriefError(
            f"{field_name} must be <= {max_length} characters"
        )
    return normalized


def _integer_us(value: Any, *, field_name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContinuityBriefError(f"{field_name} must be an integer microsecond value")
    if value < minimum:
        raise ContinuityBriefError(f"{field_name} must be >= {minimum}")
    return value


def _optional_integer_us(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    return _integer_us(value, field_name=field_name)


def _id_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ContinuityBriefError(f"{field_name} must be a list of identifiers")
    result = tuple(_identifier(item, field_name=field_name) for item in value)
    if len(result) != len(set(result)):
        raise ContinuityBriefError(f"{field_name} must not contain duplicates")
    return result


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    if unknown:
        raise ContinuityBriefError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    missing = allowed.difference(data)
    if missing:
        raise ContinuityBriefError(f"{kind} is missing fields: {sorted(missing)!r}")


@dataclass(frozen=True)
class ContinuityEvidence:
    evidence_id: str
    role: str
    path: str
    source_start_us: int | None = None
    source_end_us: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _identifier(self.evidence_id, field_name="evidence_id"))
        if not isinstance(self.role, str) or self.role not in _EVIDENCE_ROLES:
            raise ContinuityBriefError(
                f"role must be one of {sorted(_EVIDENCE_ROLES)!r}"
            )
        object.__setattr__(self, "path", _path(self.path, field_name="evidence path"))
        start = _optional_integer_us(self.source_start_us, field_name="source_start_us")
        end = _optional_integer_us(self.source_end_us, field_name="source_end_us")
        if (start is None) != (end is None):
            raise ContinuityBriefError(
                "source_start_us and source_end_us must either both be set or both be null"
            )
        if self.role != "reference" and start is None:
            raise ContinuityBriefError(
                f"{self.role} evidence requires source_start_us/source_end_us"
            )
        if start is not None and end is not None:
            if end <= start:
                raise ContinuityBriefError("evidence source_end_us must be greater than source_start_us")
            if end - start > MAX_CONTINUITY_EVIDENCE_SPAN_US:
                raise ContinuityBriefError(
                    "evidence source window exceeds the bounded continuity evidence limit"
                )
        object.__setattr__(self, "source_start_us", start)
        object.__setattr__(self, "source_end_us", end)

    def validate_against_edit(self, edit: AcceptedRangeEdit) -> None:
        start = self.source_start_us
        end = self.source_end_us
        if self.role == "reference" or start is None or end is None:
            return
        if self.role == "before" and end > edit.start_us:
            raise ContinuityBriefError(
                f"before evidence {self.evidence_id!r} extends into the requested edit range"
            )
        if self.role == "requested" and (
            start != edit.start_us or end != edit.end_us
        ):
            raise ContinuityBriefError(
                f"requested evidence {self.evidence_id!r} must exactly match the accepted edit range"
            )
        if self.role == "after" and start < edit.end_us:
            raise ContinuityBriefError(
                f"after evidence {self.evidence_id!r} starts inside the requested edit range"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "role": self.role,
            "path": self.path,
            "source_start_us": self.source_start_us,
            "source_end_us": self.source_end_us,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ContinuityEvidence":
        if not isinstance(data, Mapping):
            raise ContinuityBriefError("continuity evidence must be an object")
        allowed = {"evidence_id", "role", "path", "source_start_us", "source_end_us"}
        _strict_fields(data, allowed=allowed, kind="continuity evidence")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class MechanicalFact:
    fact_id: str
    key: str
    value: str | int | bool
    unit: str | None = None
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "fact_id", _identifier(self.fact_id, field_name="fact_id"))
        object.__setattr__(self, "key", _identifier(self.key, field_name="fact key"))
        if not isinstance(self.value, (str, int, bool)) or isinstance(self.value, float):
            raise ContinuityBriefError("mechanical fact value must be string, integer or boolean")
        if isinstance(self.value, str):
            object.__setattr__(self, "value", _text(self.value, field_name="fact value", max_length=2048))
        if self.unit is not None:
            object.__setattr__(self, "unit", _text(self.unit, field_name="fact unit", max_length=64))
        object.__setattr__(self, "evidence_ids", _id_tuple(self.evidence_ids, field_name="fact evidence_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MechanicalFact":
        if not isinstance(data, Mapping):
            raise ContinuityBriefError("mechanical fact must be an object")
        allowed = {"fact_id", "key", "value", "unit", "evidence_ids"}
        _strict_fields(data, allowed=allowed, kind="mechanical fact")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ContinuityObservation:
    observation_id: str
    kind: str
    statement: str
    confidence: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "observation_id", _identifier(self.observation_id, field_name="observation_id"))
        if not isinstance(self.kind, str) or self.kind not in _OBSERVATION_KINDS:
            raise ContinuityBriefError(
                f"observation kind must be one of {sorted(_OBSERVATION_KINDS)!r}"
            )
        object.__setattr__(self, "statement", _text(self.statement, field_name="observation statement"))
        if not isinstance(self.confidence, str) or self.confidence not in _CONFIDENCE_LEVELS:
            raise ContinuityBriefError(
                f"confidence must be one of {sorted(_CONFIDENCE_LEVELS)!r}"
            )
        evidence_ids = _id_tuple(self.evidence_ids, field_name="observation evidence_ids")
        if not evidence_ids:
            raise ContinuityBriefError("observation/inference must cite at least one evidence_id")
        object.__setattr__(self, "evidence_ids", evidence_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "kind": self.kind,
            "statement": self.statement,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ContinuityObservation":
        if not isinstance(data, Mapping):
            raise ContinuityBriefError("continuity observation must be an object")
        allowed = {"observation_id", "kind", "statement", "confidence", "evidence_ids"}
        _strict_fields(data, allowed=allowed, kind="continuity observation")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ContinuityConstraint:
    constraint_id: str
    category: str
    requirement: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraint_id", _identifier(self.constraint_id, field_name="constraint_id"))
        if not isinstance(self.category, str) or self.category not in _CONSTRAINT_CATEGORIES:
            raise ContinuityBriefError(
                f"constraint category must be one of {sorted(_CONSTRAINT_CATEGORIES)!r}"
            )
        object.__setattr__(self, "requirement", _text(self.requirement, field_name="constraint requirement"))
        object.__setattr__(self, "evidence_ids", _id_tuple(self.evidence_ids, field_name="constraint evidence_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "category": self.category,
            "requirement": self.requirement,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ContinuityConstraint":
        if not isinstance(data, Mapping):
            raise ContinuityBriefError("continuity constraint must be an object")
        allowed = {"constraint_id", "category", "requirement", "evidence_ids"}
        _strict_fields(data, allowed=allowed, kind="continuity constraint")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ReviewTarget:
    target_id: str
    criterion: str
    required: bool = True
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _identifier(self.target_id, field_name="target_id"))
        object.__setattr__(self, "criterion", _text(self.criterion, field_name="review criterion"))
        if not isinstance(self.required, bool):
            raise ContinuityBriefError("review target required must be boolean")
        object.__setattr__(self, "evidence_ids", _id_tuple(self.evidence_ids, field_name="review evidence_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "criterion": self.criterion,
            "required": self.required,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReviewTarget":
        if not isinstance(data, Mapping):
            raise ContinuityBriefError("review target must be an object")
        allowed = {"target_id", "criterion", "required", "evidence_ids"}
        _strict_fields(data, allowed=allowed, kind="review target")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class RangeContinuityBrief:
    edit_id: str
    source_path: str
    start_us: int
    end_us: int
    replacement_path: str
    evidence: tuple[ContinuityEvidence, ...] = ()
    mechanical_facts: tuple[MechanicalFact, ...] = ()
    observations: tuple[ContinuityObservation, ...] = ()
    constraints: tuple[ContinuityConstraint, ...] = ()
    review_targets: tuple[ReviewTarget, ...] = ()
    schema_version: int = CONTINUITY_BRIEF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != CONTINUITY_BRIEF_SCHEMA_VERSION
        ):
            raise ContinuityBriefError(
                f"unsupported continuity brief schema: {self.schema_version!r}"
            )
        edit = self.as_edit_identity()
        evidence = tuple(self.evidence)
        facts = tuple(self.mechanical_facts)
        observations = tuple(self.observations)
        constraints = tuple(self.constraints)
        targets = tuple(self.review_targets)
        typed_groups = (
            (evidence, ContinuityEvidence, "evidence"),
            (facts, MechanicalFact, "mechanical_facts"),
            (observations, ContinuityObservation, "observations"),
            (constraints, ContinuityConstraint, "constraints"),
            (targets, ReviewTarget, "review_targets"),
        )
        for values, expected_type, field_name in typed_groups:
            if not all(isinstance(value, expected_type) for value in values):
                raise ContinuityBriefError(f"{field_name} contains invalid values")
        for item in evidence:
            item.validate_against_edit(edit)
        self._validate_unique_ids(evidence, "evidence_id", "evidence")
        self._validate_unique_ids(facts, "fact_id", "mechanical facts")
        self._validate_unique_ids(observations, "observation_id", "observations")
        self._validate_unique_ids(constraints, "constraint_id", "constraints")
        self._validate_unique_ids(targets, "target_id", "review targets")
        known_evidence = {item.evidence_id for item in evidence}
        for collection in (facts, observations, constraints, targets):
            for item in collection:
                missing = set(item.evidence_ids).difference(known_evidence)
                if missing:
                    raise ContinuityBriefError(
                        f"{type(item).__name__} references unknown evidence IDs: {sorted(missing)!r}"
                    )
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "mechanical_facts", facts)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "review_targets", targets)

    def as_edit_identity(self) -> AcceptedRangeEdit:
        try:
            return AcceptedRangeEdit(
                edit_id=self.edit_id,
                source_path=self.source_path,
                start_us=self.start_us,
                end_us=self.end_us,
                replacement_path=self.replacement_path,
            )
        except ProjectValidationError as exc:
            raise ContinuityBriefError(str(exc)) from exc

    @staticmethod
    def _validate_unique_ids(values: tuple[Any, ...], attribute: str, kind: str) -> None:
        ids = [getattr(value, attribute) for value in values]
        if len(ids) != len(set(ids)):
            raise ContinuityBriefError(f"{kind} IDs must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "edit_id": self.edit_id,
            "source_path": self.source_path,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "replacement_path": self.replacement_path,
            "evidence": [item.to_dict() for item in self.evidence],
            "mechanical_facts": [item.to_dict() for item in self.mechanical_facts],
            "observations": [item.to_dict() for item in self.observations],
            "constraints": [item.to_dict() for item in self.constraints],
            "review_targets": [item.to_dict() for item in self.review_targets],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RangeContinuityBrief":
        if not isinstance(data, Mapping):
            raise ContinuityBriefError("RangeContinuityBrief must be an object")
        allowed = {
            "schema_version",
            "edit_id",
            "source_path",
            "start_us",
            "end_us",
            "replacement_path",
            "evidence",
            "mechanical_facts",
            "observations",
            "constraints",
            "review_targets",
        }
        _strict_fields(data, allowed=allowed, kind="RangeContinuityBrief")
        for field_name in (
            "evidence",
            "mechanical_facts",
            "observations",
            "constraints",
            "review_targets",
        ):
            if not isinstance(data[field_name], list):
                raise ContinuityBriefError(f"{field_name} must be a list")
        return cls(
            schema_version=data["schema_version"],
            edit_id=data["edit_id"],
            source_path=data["source_path"],
            start_us=data["start_us"],
            end_us=data["end_us"],
            replacement_path=data["replacement_path"],
            evidence=tuple(ContinuityEvidence.from_dict(item) for item in data["evidence"]),
            mechanical_facts=tuple(MechanicalFact.from_dict(item) for item in data["mechanical_facts"]),
            observations=tuple(ContinuityObservation.from_dict(item) for item in data["observations"]),
            constraints=tuple(ContinuityConstraint.from_dict(item) for item in data["constraints"]),
            review_targets=tuple(ReviewTarget.from_dict(item) for item in data["review_targets"]),
        )


@dataclass(frozen=True)
class RangeContinuityBriefState:
    briefs: tuple[RangeContinuityBrief, ...] = ()
    schema_version: int = CONTINUITY_BRIEF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != CONTINUITY_BRIEF_SCHEMA_VERSION
        ):
            raise ContinuityBriefError(
                f"unsupported continuity brief state schema: {self.schema_version!r}"
            )
        briefs = tuple(self.briefs)
        if not all(isinstance(brief, RangeContinuityBrief) for brief in briefs):
            raise ContinuityBriefError("briefs must contain RangeContinuityBrief values")
        ids = [brief.edit_id for brief in briefs]
        if len(ids) != len(set(ids)):
            raise ContinuityBriefError("only one RangeContinuityBrief may exist per edit_id")
        object.__setattr__(self, "briefs", tuple(sorted(briefs, key=lambda item: item.edit_id)))

    def get(self, edit_id: str) -> RangeContinuityBrief:
        normalized = _identifier(edit_id, field_name="edit_id")
        for brief in self.briefs:
            if brief.edit_id == normalized:
                return brief
        raise ContinuityBriefNotFound(normalized)

    def upsert(self, brief: RangeContinuityBrief) -> "RangeContinuityBriefState":
        return RangeContinuityBriefState(
            briefs=tuple(item for item in self.briefs if item.edit_id != brief.edit_id) + (brief,)
        )

    def remove(self, edit_id: str) -> "RangeContinuityBriefState":
        normalized = _identifier(edit_id, field_name="edit_id")
        remaining = tuple(item for item in self.briefs if item.edit_id != normalized)
        if len(remaining) == len(self.briefs):
            raise ContinuityBriefNotFound(normalized)
        return RangeContinuityBriefState(briefs=remaining)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "briefs": [brief.to_dict() for brief in self.briefs],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RangeContinuityBriefState":
        if not isinstance(data, Mapping):
            raise ContinuityBriefError("continuity brief state must be an object")
        allowed = {"schema_version", "briefs"}
        _strict_fields(data, allowed=allowed, kind="continuity brief state")
        if not isinstance(data["briefs"], list):
            raise ContinuityBriefError("briefs must be a list")
        return cls(
            schema_version=data["schema_version"],
            briefs=tuple(RangeContinuityBrief.from_dict(item) for item in data["briefs"]),
        )


class RangeContinuityBriefStore:
    """Atomic typed persistence for provider-neutral continuity briefs."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _state_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                CONTINUITY_BRIEF_PATH,
                must_exist=False,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise ContinuityBriefError(str(exc)) from exc

    def load(self, project_id: str, *, validate_references: bool = False) -> RangeContinuityBriefState:
        path = self._state_path(project_id)
        if not path.exists():
            return RangeContinuityBriefState()
        if not path.is_file() or path.is_symlink():
            raise ContinuityBriefError("continuity brief path must be a regular project file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContinuityBriefError("continuity brief state is malformed JSON") from exc
        except OSError as exc:
            raise ContinuityBriefError("continuity brief state could not be read") from exc
        state = RangeContinuityBriefState.from_dict(data)
        if validate_references:
            self._validate_state(project_id, state)
        return state

    def _write(self, project_id: str, state: RangeContinuityBriefState) -> RangeContinuityBriefState:
        self.project_store._atomic_write_json(self._state_path(project_id), state.to_dict())
        return state

    def upsert(self, project_id: str, brief: RangeContinuityBrief) -> RangeContinuityBriefState:
        if not isinstance(brief, RangeContinuityBrief):
            raise ContinuityBriefError("upsert requires RangeContinuityBrief")
        with self.project_store._lock:
            current = self.load(project_id)
            self._validate_brief(project_id, brief)
            return self._write(project_id, current.upsert(brief))

    def remove(self, project_id: str, edit_id: str) -> RangeContinuityBriefState:
        with self.project_store._lock:
            current = self.load(project_id)
            return self._write(project_id, current.remove(edit_id))

    def validate_project(self, project_id: str) -> RangeContinuityBriefState:
        return self.load(project_id, validate_references=True)

    def _accepted_edit(self, project_id: str, edit_id: str) -> AcceptedRangeEdit:
        edit_state = RangeEditStateStore(self.project_store).load(project_id)
        normalized = _identifier(edit_id, field_name="edit_id")
        for edit in edit_state.edits:
            if edit.edit_id == normalized:
                return edit
        raise ContinuityBriefError(
            f"continuity brief target edit {normalized!r} is not currently accepted"
        )

    def _validate_brief(self, project_id: str, brief: RangeContinuityBrief) -> None:
        accepted = self._accepted_edit(project_id, brief.edit_id)
        if brief.as_edit_identity() != accepted:
            raise ContinuityBriefError(
                f"continuity brief identity does not exactly match accepted edit {brief.edit_id!r}"
            )
        for evidence in brief.evidence:
            try:
                resolved = self.project_store.resolve_project_file(
                    project_id,
                    evidence.path,
                    must_exist=True,
                    allowed_roots=_EVIDENCE_ROOTS,
                )
            except (ProjectValidationError, ProjectStoreError) as exc:
                raise ContinuityBriefError(
                    f"evidence {evidence.evidence_id!r} is not a valid existing project file: {exc}"
                ) from exc
            if not resolved.is_file() or resolved.is_symlink():
                raise ContinuityBriefError(
                    f"evidence {evidence.evidence_id!r} must be a regular project file"
                )

    def _validate_state(self, project_id: str, state: RangeContinuityBriefState) -> None:
        for brief in state.briefs:
            self._validate_brief(project_id, brief)
