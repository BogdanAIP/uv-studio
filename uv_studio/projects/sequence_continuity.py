"""Optional provider-neutral linked-shot continuity state for Stage 6."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Any, Mapping

from .media_integrity import MediaIntegrityError, verify_registered_media_bytes
from .models import (
    ProjectReference,
    ProjectValidationError,
    validate_identifier,
    validate_project_relative_path,
)
from .store import ProjectStore, ProjectStoreError

SEQUENCE_CONTINUITY_SCHEMA_VERSION = 1
SEQUENCE_CONTINUITY_PATH = "timeline/sequence-continuity.json"
MAX_SEQUENCES = 64
MAX_SHOTS_PER_SEQUENCE = 256
MAX_TAKES_PER_SEQUENCE = 1024
MAX_REVIEWS_PER_SEQUENCE = 2048
MAX_RULES_PER_PLAN = 64
MAX_REVIEW_TARGETS_PER_PLAN = 64
MAX_OBSERVATIONS_PER_REVIEW = 128
MAX_CONTEXT_WINDOW_US = 10_000_000
_RULE_CATEGORIES = frozenset(
    {"visual", "motion", "audio", "timing", "content", "technical", "style"}
)
_CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
_OBSERVATION_KINDS = frozenset({"observation", "inference"})
_REVIEW_OUTCOMES = frozenset({"pass", "fail", "uncertain"})
_REVIEW_VERDICTS = frozenset({"approved", "needs_revision", "rejected"})
_TAKE_STATUSES = frozenset({"prepared", "accepted", "rejected"})
_MEDIA_ROOTS = frozenset({"sources", "assets", "artifacts", "exports"})


class SequenceContinuityError(ProjectValidationError):
    """Invalid or inconsistent sequence-continuity state."""


class SequenceNotFound(SequenceContinuityError):
    pass


class SequenceShotNotFound(SequenceContinuityError):
    pass


class SequenceTakeNotFound(SequenceContinuityError):
    pass


class SequenceReviewNotFound(SequenceContinuityError):
    pass


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise SequenceContinuityError(str(exc)) from exc


def _text(value: Any, *, field_name: str, maximum: int = 4000) -> str:
    if not isinstance(value, str):
        raise SequenceContinuityError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise SequenceContinuityError(f"{field_name} must not be empty")
    if len(normalized) > maximum:
        raise SequenceContinuityError(f"{field_name} must be <= {maximum} characters")
    return normalized


def _optional_text(value: Any, *, field_name: str, maximum: int = 4000) -> str | None:
    if value is None:
        return None
    return _text(value, field_name=field_name, maximum=maximum)


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise SequenceContinuityError(f"{field_name} must be a 64-character sha256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise SequenceContinuityError(f"{field_name} must be hexadecimal sha256") from exc
    return value.lower()


def _positive_int(value: Any, *, field_name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SequenceContinuityError(f"{field_name} must be an integer >= {minimum}")
    return value


def _nonnegative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SequenceContinuityError(f"{field_name} must be a non-negative integer")
    return value


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    missing = allowed.difference(data)
    if unknown:
        raise SequenceContinuityError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    if missing:
        raise SequenceContinuityError(f"{kind} is missing fields: {sorted(missing)!r}")


def _canonical_sha(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True)
class SequenceContinuityRule:
    rule_id: str
    category: str
    requirement: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _identifier(self.rule_id, field_name="rule_id"))
        if not isinstance(self.category, str) or self.category not in _RULE_CATEGORIES:
            raise SequenceContinuityError(
                f"rule category must be one of {sorted(_RULE_CATEGORIES)!r}"
            )
        object.__setattr__(
            self, "requirement", _text(self.requirement, field_name="continuity requirement")
        )

    def to_dict(self) -> dict[str, Any]:
        return {"rule_id": self.rule_id, "category": self.category, "requirement": self.requirement}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceContinuityRule":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("continuity rule must be an object")
        allowed = {"rule_id", "category", "requirement"}
        _strict_fields(data, allowed=allowed, kind="continuity rule")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class SequenceReviewTarget:
    target_id: str
    criterion: str
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_id", _identifier(self.target_id, field_name="review target_id")
        )
        object.__setattr__(
            self, "criterion", _text(self.criterion, field_name="review criterion")
        )
        if not isinstance(self.required, bool):
            raise SequenceContinuityError("review target required must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {"target_id": self.target_id, "criterion": self.criterion, "required": self.required}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceReviewTarget":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("review target must be an object")
        allowed = {"target_id", "criterion", "required"}
        _strict_fields(data, allowed=allowed, kind="review target")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class SequenceObservation:
    observation_id: str
    kind: str
    category: str
    statement: str
    confidence: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "observation_id", _identifier(self.observation_id, field_name="observation_id")
        )
        if not isinstance(self.kind, str) or self.kind not in _OBSERVATION_KINDS:
            raise SequenceContinuityError(
                f"observation kind must be one of {sorted(_OBSERVATION_KINDS)!r}"
            )
        if not isinstance(self.category, str) or self.category not in _RULE_CATEGORIES:
            raise SequenceContinuityError(
                f"observation category must be one of {sorted(_RULE_CATEGORIES)!r}"
            )
        object.__setattr__(
            self, "statement", _text(self.statement, field_name="observation statement")
        )
        if not isinstance(self.confidence, str) or self.confidence not in _CONFIDENCE_LEVELS:
            raise SequenceContinuityError(
                f"confidence must be one of {sorted(_CONFIDENCE_LEVELS)!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "kind": self.kind,
            "category": self.category,
            "statement": self.statement,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceObservation":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("sequence observation must be an object")
        allowed = {"observation_id", "kind", "category", "statement", "confidence"}
        _strict_fields(data, allowed=allowed, kind="sequence observation")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class SequenceReviewResult:
    target_id: str
    outcome: str
    note: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_id", _identifier(self.target_id, field_name="review result target_id")
        )
        if not isinstance(self.outcome, str) or self.outcome not in _REVIEW_OUTCOMES:
            raise SequenceContinuityError(
                f"review outcome must be one of {sorted(_REVIEW_OUTCOMES)!r}"
            )
        object.__setattr__(self, "note", _optional_text(self.note, field_name="review result note"))

    def to_dict(self) -> dict[str, Any]:
        return {"target_id": self.target_id, "outcome": self.outcome, "note": self.note}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceReviewResult":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("review result must be an object")
        allowed = {"target_id", "outcome", "note"}
        _strict_fields(data, allowed=allowed, kind="review result")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class SequenceShotPlan:
    shot_id: str
    order: int
    intent: str
    anchor_take_id: str | None = None
    anchor_take_sha256: str | None = None
    locks: tuple[SequenceContinuityRule, ...] = ()
    allowed_changes: tuple[SequenceContinuityRule, ...] = ()
    review_targets: tuple[SequenceReviewTarget, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="shot_id"))
        object.__setattr__(self, "order", _nonnegative_int(self.order, field_name="shot order"))
        object.__setattr__(self, "intent", _text(self.intent, field_name="shot intent"))
        if (self.anchor_take_id is None) != (self.anchor_take_sha256 is None):
            raise SequenceContinuityError(
                "anchor_take_id and anchor_take_sha256 must either both be set or both be null"
            )
        if self.anchor_take_id is not None:
            object.__setattr__(
                self, "anchor_take_id", _identifier(self.anchor_take_id, field_name="anchor_take_id")
            )
            object.__setattr__(
                self,
                "anchor_take_sha256",
                _sha256(self.anchor_take_sha256, field_name="anchor_take_sha256"),
            )
        locks = tuple(self.locks)
        allowed_changes = tuple(self.allowed_changes)
        targets = tuple(self.review_targets)
        if len(locks) > MAX_RULES_PER_PLAN or len(allowed_changes) > MAX_RULES_PER_PLAN:
            raise SequenceContinuityError(
                f"locks/allowed_changes must each contain at most {MAX_RULES_PER_PLAN} items"
            )
        if len(targets) > MAX_REVIEW_TARGETS_PER_PLAN:
            raise SequenceContinuityError(
                f"review_targets must contain at most {MAX_REVIEW_TARGETS_PER_PLAN} items"
            )
        if not all(isinstance(item, SequenceContinuityRule) for item in (*locks, *allowed_changes)):
            raise SequenceContinuityError("locks/allowed_changes contain invalid values")
        if not all(isinstance(item, SequenceReviewTarget) for item in targets):
            raise SequenceContinuityError("review_targets contain invalid values")
        rule_ids = [item.rule_id for item in (*locks, *allowed_changes)]
        if len(rule_ids) != len(set(rule_ids)):
            raise SequenceContinuityError("lock/allowed-change rule IDs must be unique")
        target_ids = [item.target_id for item in targets]
        if len(target_ids) != len(set(target_ids)):
            raise SequenceContinuityError("review target IDs must be unique")
        object.__setattr__(self, "locks", locks)
        object.__setattr__(self, "allowed_changes", allowed_changes)
        object.__setattr__(self, "review_targets", targets)

    def identity_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "order": self.order,
            "intent": self.intent,
            "anchor_take_id": self.anchor_take_id,
            "anchor_take_sha256": self.anchor_take_sha256,
            "locks": [item.to_dict() for item in self.locks],
            "allowed_changes": [item.to_dict() for item in self.allowed_changes],
            "review_targets": [item.to_dict() for item in self.review_targets],
        }

    @property
    def revision_sha256(self) -> str:
        return _canonical_sha(self.identity_dict())

    def to_dict(self) -> dict[str, Any]:
        payload = self.identity_dict()
        payload["revision_sha256"] = self.revision_sha256
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceShotPlan":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("shot plan must be an object")
        allowed = {
            "shot_id", "order", "intent", "anchor_take_id", "anchor_take_sha256",
            "locks", "allowed_changes", "review_targets", "revision_sha256",
        }
        _strict_fields(data, allowed=allowed, kind="shot plan")
        for field_name in ("locks", "allowed_changes", "review_targets"):
            if not isinstance(data[field_name], list):
                raise SequenceContinuityError(f"{field_name} must be a list")
        value = cls(
            shot_id=data["shot_id"],
            order=data["order"],
            intent=data["intent"],
            anchor_take_id=data["anchor_take_id"],
            anchor_take_sha256=data["anchor_take_sha256"],
            locks=tuple(SequenceContinuityRule.from_dict(item) for item in data["locks"]),
            allowed_changes=tuple(
                SequenceContinuityRule.from_dict(item) for item in data["allowed_changes"]
            ),
            review_targets=tuple(
                SequenceReviewTarget.from_dict(item) for item in data["review_targets"]
            ),
        )
        if _sha256(data["revision_sha256"], field_name="revision_sha256") != value.revision_sha256:
            raise SequenceContinuityError("stored shot plan revision does not match plan contents")
        return value


@dataclass(frozen=True)
class SequenceTakeReview:
    review_id: str
    take_id: str
    shot_id: str
    plan_revision_sha256: str
    take_sha256: str
    anchor_take_id: str | None
    anchor_take_sha256: str | None
    verdict: str
    results: tuple[SequenceReviewResult, ...] = ()
    observations: tuple[SequenceObservation, ...] = ()
    note: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "review_id", _identifier(self.review_id, field_name="review_id"))
        object.__setattr__(self, "take_id", _identifier(self.take_id, field_name="take_id"))
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="shot_id"))
        object.__setattr__(
            self,
            "plan_revision_sha256",
            _sha256(self.plan_revision_sha256, field_name="plan_revision_sha256"),
        )
        object.__setattr__(self, "take_sha256", _sha256(self.take_sha256, field_name="take_sha256"))
        if (self.anchor_take_id is None) != (self.anchor_take_sha256 is None):
            raise SequenceContinuityError(
                "review anchor_take_id and anchor_take_sha256 must both be set or both null"
            )
        if self.anchor_take_id is not None:
            object.__setattr__(
                self, "anchor_take_id", _identifier(self.anchor_take_id, field_name="review anchor_take_id")
            )
            object.__setattr__(
                self,
                "anchor_take_sha256",
                _sha256(self.anchor_take_sha256, field_name="review anchor_take_sha256"),
            )
        if not isinstance(self.verdict, str) or self.verdict not in _REVIEW_VERDICTS:
            raise SequenceContinuityError(
                f"review verdict must be one of {sorted(_REVIEW_VERDICTS)!r}"
            )
        results = tuple(self.results)
        observations = tuple(self.observations)
        if not all(isinstance(item, SequenceReviewResult) for item in results):
            raise SequenceContinuityError("review results contain invalid values")
        if not all(isinstance(item, SequenceObservation) for item in observations):
            raise SequenceContinuityError("review observations contain invalid values")
        if len(observations) > MAX_OBSERVATIONS_PER_REVIEW:
            raise SequenceContinuityError(
                f"review observations must contain at most {MAX_OBSERVATIONS_PER_REVIEW} items"
            )
        target_ids = [item.target_id for item in results]
        observation_ids = [item.observation_id for item in observations]
        if len(target_ids) != len(set(target_ids)):
            raise SequenceContinuityError("review result target IDs must be unique")
        if len(observation_ids) != len(set(observation_ids)):
            raise SequenceContinuityError("review observation IDs must be unique")
        object.__setattr__(self, "results", results)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "note", _optional_text(self.note, field_name="review note"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "take_id": self.take_id,
            "shot_id": self.shot_id,
            "plan_revision_sha256": self.plan_revision_sha256,
            "take_sha256": self.take_sha256,
            "anchor_take_id": self.anchor_take_id,
            "anchor_take_sha256": self.anchor_take_sha256,
            "verdict": self.verdict,
            "results": [item.to_dict() for item in self.results],
            "observations": [item.to_dict() for item in self.observations],
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceTakeReview":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("take review must be an object")
        allowed = {
            "review_id", "take_id", "shot_id", "plan_revision_sha256", "take_sha256",
            "anchor_take_id", "anchor_take_sha256", "verdict", "results", "observations", "note",
        }
        _strict_fields(data, allowed=allowed, kind="take review")
        if not isinstance(data["results"], list) or not isinstance(data["observations"], list):
            raise SequenceContinuityError("review results/observations must be lists")
        return cls(
            review_id=data["review_id"],
            take_id=data["take_id"],
            shot_id=data["shot_id"],
            plan_revision_sha256=data["plan_revision_sha256"],
            take_sha256=data["take_sha256"],
            anchor_take_id=data["anchor_take_id"],
            anchor_take_sha256=data["anchor_take_sha256"],
            verdict=data["verdict"],
            results=tuple(SequenceReviewResult.from_dict(item) for item in data["results"]),
            observations=tuple(SequenceObservation.from_dict(item) for item in data["observations"]),
            note=data["note"],
        )


@dataclass(frozen=True)
class SequenceTake:
    take_id: str
    shot_id: str
    reference_id: str
    reference_path: str
    reference_kind: str
    artifact_sha256: str
    size_bytes: int
    plan_revision_sha256: str
    status: str = "prepared"
    current_review_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "take_id", _identifier(self.take_id, field_name="take_id"))
        object.__setattr__(self, "shot_id", _identifier(self.shot_id, field_name="shot_id"))
        object.__setattr__(
            self, "reference_id", _identifier(self.reference_id, field_name="reference_id")
        )
        try:
            canonical_path = validate_project_relative_path(self.reference_path)
        except ProjectValidationError as exc:
            raise SequenceContinuityError(str(exc)) from exc
        object.__setattr__(self, "reference_path", canonical_path)
        if self.reference_kind not in {"source", "artifact"}:
            raise SequenceContinuityError("take reference_kind must be source or artifact")
        object.__setattr__(
            self, "artifact_sha256", _sha256(self.artifact_sha256, field_name="artifact_sha256")
        )
        object.__setattr__(self, "size_bytes", _positive_int(self.size_bytes, field_name="size_bytes"))
        object.__setattr__(
            self,
            "plan_revision_sha256",
            _sha256(self.plan_revision_sha256, field_name="plan_revision_sha256"),
        )
        if not isinstance(self.status, str) or self.status not in _TAKE_STATUSES:
            raise SequenceContinuityError(
                f"take status must be one of {sorted(_TAKE_STATUSES)!r}"
            )
        if self.current_review_id is not None:
            object.__setattr__(
                self,
                "current_review_id",
                _identifier(self.current_review_id, field_name="current_review_id"),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "take_id": self.take_id,
            "shot_id": self.shot_id,
            "reference_id": self.reference_id,
            "reference_path": self.reference_path,
            "reference_kind": self.reference_kind,
            "artifact_sha256": self.artifact_sha256,
            "size_bytes": self.size_bytes,
            "plan_revision_sha256": self.plan_revision_sha256,
            "status": self.status,
            "current_review_id": self.current_review_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceTake":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("sequence take must be an object")
        allowed = {
            "take_id", "shot_id", "reference_id", "reference_path", "reference_kind",
            "artifact_sha256", "size_bytes", "plan_revision_sha256", "status", "current_review_id",
        }
        _strict_fields(data, allowed=allowed, kind="sequence take")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class SequenceRecord:
    sequence_id: str
    title: str
    plans: tuple[SequenceShotPlan, ...] = ()
    takes: tuple[SequenceTake, ...] = ()
    reviews: tuple[SequenceTakeReview, ...] = ()
    anchor_take_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "sequence_id", _identifier(self.sequence_id, field_name="sequence_id")
        )
        object.__setattr__(
            self, "title", _text(self.title, field_name="sequence title", maximum=512)
        )
        plans, takes, reviews = tuple(self.plans), tuple(self.takes), tuple(self.reviews)
        if len(plans) > MAX_SHOTS_PER_SEQUENCE:
            raise SequenceContinuityError(
                f"a sequence may contain at most {MAX_SHOTS_PER_SEQUENCE} shot plans"
            )
        if len(takes) > MAX_TAKES_PER_SEQUENCE:
            raise SequenceContinuityError(
                f"a sequence may contain at most {MAX_TAKES_PER_SEQUENCE} takes"
            )
        if len(reviews) > MAX_REVIEWS_PER_SEQUENCE:
            raise SequenceContinuityError(
                f"a sequence may contain at most {MAX_REVIEWS_PER_SEQUENCE} reviews"
            )
        if not all(isinstance(item, SequenceShotPlan) for item in plans):
            raise SequenceContinuityError("plans contain invalid values")
        if not all(isinstance(item, SequenceTake) for item in takes):
            raise SequenceContinuityError("takes contain invalid values")
        if not all(isinstance(item, SequenceTakeReview) for item in reviews):
            raise SequenceContinuityError("reviews contain invalid values")
        shot_ids = [item.shot_id for item in plans]
        orders = [item.order for item in plans]
        take_ids = [item.take_id for item in takes]
        review_ids = [item.review_id for item in reviews]
        for values, kind in ((shot_ids, "shot IDs"), (orders, "shot orders"), (take_ids, "take IDs"), (review_ids, "review IDs")):
            if len(values) != len(set(values)):
                raise SequenceContinuityError(f"{kind} must be unique")
        plans_by_id = {item.shot_id: item for item in plans}
        takes_by_id = {item.take_id: item for item in takes}
        reviews_by_id = {item.review_id: item for item in reviews}
        for take in takes:
            if take.shot_id not in plans_by_id:
                raise SequenceContinuityError(
                    f"take {take.take_id!r} references unknown shot {take.shot_id!r}"
                )
            if take.current_review_id is not None:
                review = reviews_by_id.get(take.current_review_id)
                if review is None or review.take_id != take.take_id:
                    raise SequenceContinuityError(
                        f"take {take.take_id!r} current_review_id is invalid"
                    )
        accepted_by_shot: dict[str, str] = {}
        for take in takes:
            if take.status != "accepted":
                continue
            if take.shot_id in accepted_by_shot:
                raise SequenceContinuityError(
                    f"shot {take.shot_id!r} has more than one accepted take"
                )
            accepted_by_shot[take.shot_id] = take.take_id
            if take.current_review_id is None:
                raise SequenceContinuityError(
                    f"accepted take {take.take_id!r} requires a current approved review"
                )
            review = reviews_by_id[take.current_review_id]
            if review.verdict != "approved":
                raise SequenceContinuityError(
                    f"accepted take {take.take_id!r} current review is not approved"
                )
            if review.take_sha256 != take.artifact_sha256 or review.plan_revision_sha256 != take.plan_revision_sha256:
                raise SequenceContinuityError(
                    f"accepted take {take.take_id!r} review binding is stale"
                )
        for review in reviews:
            take = takes_by_id.get(review.take_id)
            if take is None:
                raise SequenceContinuityError(
                    f"review {review.review_id!r} references unknown take"
                )
            if review.shot_id != take.shot_id or review.take_sha256 != take.artifact_sha256:
                raise SequenceContinuityError(
                    f"review {review.review_id!r} does not match take identity"
                )
        for plan in plans:
            if plan.anchor_take_id is None:
                continue
            anchor = takes_by_id.get(plan.anchor_take_id)
            if anchor is None or anchor.status != "accepted":
                raise SequenceContinuityError(
                    f"shot {plan.shot_id!r} anchor must be an accepted take"
                )
            if anchor.artifact_sha256 != plan.anchor_take_sha256:
                raise SequenceContinuityError(
                    f"shot {plan.shot_id!r} anchor sha does not match accepted take"
                )
            if plans_by_id[anchor.shot_id].order >= plan.order:
                raise SequenceContinuityError(
                    f"shot {plan.shot_id!r} anchor must come from an earlier shot"
                )
        anchor_take_id = self.anchor_take_id
        if anchor_take_id is not None:
            anchor_take_id = _identifier(anchor_take_id, field_name="sequence anchor_take_id")
            anchor = takes_by_id.get(anchor_take_id)
            if anchor is None or anchor.status != "accepted":
                raise SequenceContinuityError(
                    "sequence anchor_take_id must reference an accepted take"
                )
        object.__setattr__(self, "plans", plans)
        object.__setattr__(self, "takes", takes)
        object.__setattr__(self, "reviews", reviews)
        object.__setattr__(self, "anchor_take_id", anchor_take_id)

    def plan(self, shot_id: str) -> SequenceShotPlan:
        for item in self.plans:
            if item.shot_id == shot_id:
                return item
        raise SequenceShotNotFound(shot_id)

    def take(self, take_id: str) -> SequenceTake:
        for item in self.takes:
            if item.take_id == take_id:
                return item
        raise SequenceTakeNotFound(take_id)

    def review(self, review_id: str) -> SequenceTakeReview:
        for item in self.reviews:
            if item.review_id == review_id:
                return item
        raise SequenceReviewNotFound(review_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "title": self.title,
            "plans": [item.to_dict() for item in sorted(self.plans, key=lambda item: item.order)],
            "takes": [item.to_dict() for item in self.takes],
            "reviews": [item.to_dict() for item in self.reviews],
            "anchor_take_id": self.anchor_take_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceRecord":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("sequence record must be an object")
        allowed = {"sequence_id", "title", "plans", "takes", "reviews", "anchor_take_id"}
        _strict_fields(data, allowed=allowed, kind="sequence record")
        for field_name in ("plans", "takes", "reviews"):
            if not isinstance(data[field_name], list):
                raise SequenceContinuityError(f"{field_name} must be a list")
        return cls(
            sequence_id=data["sequence_id"],
            title=data["title"],
            plans=tuple(SequenceShotPlan.from_dict(item) for item in data["plans"]),
            takes=tuple(SequenceTake.from_dict(item) for item in data["takes"]),
            reviews=tuple(SequenceTakeReview.from_dict(item) for item in data["reviews"]),
            anchor_take_id=data["anchor_take_id"],
        )


@dataclass(frozen=True)
class SequenceContinuityState:
    sequences: tuple[SequenceRecord, ...] = ()
    schema_version: int = SEQUENCE_CONTINUITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, int) or self.schema_version != SEQUENCE_CONTINUITY_SCHEMA_VERSION:
            raise SequenceContinuityError(
                f"unsupported sequence continuity schema: {self.schema_version!r}"
            )
        sequences = tuple(self.sequences)
        if len(sequences) > MAX_SEQUENCES:
            raise SequenceContinuityError(
                f"project may contain at most {MAX_SEQUENCES} continuity sequences"
            )
        if not all(isinstance(item, SequenceRecord) for item in sequences):
            raise SequenceContinuityError("sequences contain invalid values")
        ids = [item.sequence_id for item in sequences]
        if len(ids) != len(set(ids)):
            raise SequenceContinuityError("sequence IDs must be unique")
        object.__setattr__(self, "sequences", sequences)

    def sequence(self, sequence_id: str) -> SequenceRecord:
        for item in self.sequences:
            if item.sequence_id == sequence_id:
                return item
        raise SequenceNotFound(sequence_id)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "sequences": [item.to_dict() for item in self.sequences]}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceContinuityState":
        if not isinstance(data, Mapping):
            raise SequenceContinuityError("sequence continuity state must be an object")
        allowed = {"schema_version", "sequences"}
        _strict_fields(data, allowed=allowed, kind="sequence continuity state")
        if not isinstance(data["sequences"], list):
            raise SequenceContinuityError("sequences must be a list")
        return cls(
            schema_version=data["schema_version"],
            sequences=tuple(SequenceRecord.from_dict(item) for item in data["sequences"]),
        )


class SequenceContinuityStore:
    """Atomic Project Store facade for optional linked-shot continuity state."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _path(self, project_id: str):
        return self.project_store.resolve_project_file(
            project_id, SEQUENCE_CONTINUITY_PATH, allowed_roots=("timeline",)
        )

    def load(self, project_id: str, *, validate_current: bool = False) -> SequenceContinuityState:
        path = self._path(project_id)
        if not path.exists():
            state = SequenceContinuityState()
        else:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                state = SequenceContinuityState.from_dict(raw)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                raise SequenceContinuityError(
                    f"invalid sequence continuity state: {path}: {exc}"
                ) from exc
        if validate_current:
            self.validate_current(project_id, state)
        return state

    def validate_current(
        self, project_id: str, state: SequenceContinuityState | None = None
    ) -> None:
        state = state or self.load(project_id)
        for sequence in state.sequences:
            for take in sequence.takes:
                if take.status == "accepted":
                    self._verify_take_current(project_id, take)

    def create_sequence(
        self, project_id: str, *, title: str, sequence_id: str | None = None
    ) -> SequenceRecord:
        sequence = SequenceRecord(
            sequence_id=sequence_id or f"seq_{uuid.uuid4().hex}", title=title
        )
        with self.project_store._lock:
            state = self.load(project_id)
            if any(item.sequence_id == sequence.sequence_id for item in state.sequences):
                raise SequenceContinuityError(
                    f"sequence {sequence.sequence_id!r} already exists"
                )
            self._save(
                project_id,
                SequenceContinuityState(sequences=(*state.sequences, sequence)),
            )
        return sequence

    def upsert_plan(
        self,
        project_id: str,
        *,
        sequence_id: str,
        shot_id: str,
        order: int,
        intent: str,
        anchor_take_id: str | None,
        locks: tuple[SequenceContinuityRule, ...],
        allowed_changes: tuple[SequenceContinuityRule, ...],
        review_targets: tuple[SequenceReviewTarget, ...],
    ) -> SequenceShotPlan:
        with self.project_store._lock:
            state = self.load(project_id)
            sequence = state.sequence(sequence_id)
            anchor_sha: str | None = None
            if anchor_take_id is not None:
                anchor = sequence.take(anchor_take_id)
                if anchor.status != "accepted":
                    raise SequenceContinuityError("shot anchor must be an accepted take")
                self._verify_take_current(project_id, anchor)
                anchor_sha = anchor.artifact_sha256
            plan = SequenceShotPlan(
                shot_id=shot_id,
                order=order,
                intent=intent,
                anchor_take_id=anchor_take_id,
                anchor_take_sha256=anchor_sha,
                locks=locks,
                allowed_changes=allowed_changes,
                review_targets=review_targets,
            )
            previous = next(
                (item for item in sequence.plans if item.shot_id == plan.shot_id), None
            )
            if previous is not None and previous.revision_sha256 != plan.revision_sha256:
                if any(
                    take.shot_id == plan.shot_id and take.status == "accepted"
                    for take in sequence.takes
                ):
                    raise SequenceContinuityError(
                        "cannot change a shot plan after a take for that shot was accepted"
                    )
            plans = tuple(
                item for item in sequence.plans if item.shot_id != plan.shot_id
            ) + (plan,)
            updated_sequence = replace(sequence, plans=plans)
            self._save(project_id, self._replace_sequence(state, updated_sequence))
            return plan

    def register_take(
        self,
        project_id: str,
        *,
        sequence_id: str,
        shot_id: str,
        reference_id: str,
        take_id: str | None = None,
    ) -> SequenceTake:
        with self.project_store._lock:
            state = self.load(project_id)
            sequence = state.sequence(sequence_id)
            plan = sequence.plan(shot_id)
            reference, path, reference_kind = self._resolve_reference(project_id, reference_id)
            try:
                identity = verify_registered_media_bytes(path, reference.metadata)
            except MediaIntegrityError as exc:
                raise SequenceContinuityError(str(exc)) from exc
            value = SequenceTake(
                take_id=take_id or f"take_{uuid.uuid4().hex}",
                shot_id=shot_id,
                reference_id=reference.id,
                reference_path=reference.path,
                reference_kind=reference_kind,
                artifact_sha256=identity.sha256,
                size_bytes=identity.size_bytes,
                plan_revision_sha256=plan.revision_sha256,
            )
            if any(item.take_id == value.take_id for item in sequence.takes):
                raise SequenceContinuityError(f"take {value.take_id!r} already exists")
            updated_sequence = replace(sequence, takes=(*sequence.takes, value))
            self._save(project_id, self._replace_sequence(state, updated_sequence))
            return value

    def review_take(
        self,
        project_id: str,
        *,
        sequence_id: str,
        take_id: str,
        verdict: str,
        results: tuple[SequenceReviewResult, ...],
        observations: tuple[SequenceObservation, ...] = (),
        note: str | None = None,
    ) -> SequenceTakeReview:
        with self.project_store._lock:
            state = self.load(project_id)
            sequence = state.sequence(sequence_id)
            take = sequence.take(take_id)
            if take.status != "prepared":
                raise SequenceContinuityError("only a prepared take can be reviewed")
            plan = sequence.plan(take.shot_id)
            if take.plan_revision_sha256 != plan.revision_sha256:
                raise SequenceContinuityError(
                    "take was prepared against an older shot plan and must be replaced"
                )
            self._verify_plan_anchor_current(project_id, sequence, plan)
            self._verify_take_current(project_id, take)
            results = tuple(results)
            expected_ids = {item.target_id for item in plan.review_targets}
            actual_ids = {item.target_id for item in results}
            if expected_ids != actual_ids or len(results) != len(actual_ids):
                raise SequenceContinuityError(
                    "review results must cover each current review target exactly once"
                )
            by_id = {item.target_id: item for item in results}
            if verdict == "approved":
                failing_required = [
                    target.target_id
                    for target in plan.review_targets
                    if target.required and by_id[target.target_id].outcome != "pass"
                ]
                if failing_required:
                    raise SequenceContinuityError(
                        "approved review requires pass for all required targets: "
                        f"{sorted(failing_required)!r}"
                    )
            review = SequenceTakeReview(
                review_id=f"seqrev_{uuid.uuid4().hex}",
                take_id=take.take_id,
                shot_id=take.shot_id,
                plan_revision_sha256=plan.revision_sha256,
                take_sha256=take.artifact_sha256,
                anchor_take_id=plan.anchor_take_id,
                anchor_take_sha256=plan.anchor_take_sha256,
                verdict=verdict,
                results=results,
                observations=tuple(observations),
                note=note,
            )
            reviewed_take = replace(
                take,
                status="rejected" if verdict == "rejected" else take.status,
                current_review_id=review.review_id,
            )
            takes = tuple(
                reviewed_take if item.take_id == take.take_id else item
                for item in sequence.takes
            )
            updated_sequence = replace(
                sequence, takes=takes, reviews=(*sequence.reviews, review)
            )
            self._save(project_id, self._replace_sequence(state, updated_sequence))
            return review

    def accept_take(
        self, project_id: str, *, sequence_id: str, review_id: str
    ) -> SequenceTake:
        with self.project_store._lock:
            state = self.load(project_id)
            sequence = state.sequence(sequence_id)
            review = sequence.review(review_id)
            take = sequence.take(review.take_id)
            if take.status != "prepared":
                raise SequenceContinuityError("only a prepared take can be accepted")
            if take.current_review_id != review.review_id:
                raise SequenceContinuityError("only the current take review can be accepted")
            if review.verdict != "approved":
                raise SequenceContinuityError("only an approved review can be accepted")
            plan = sequence.plan(take.shot_id)
            if take.plan_revision_sha256 != plan.revision_sha256 or review.plan_revision_sha256 != plan.revision_sha256:
                raise SequenceContinuityError("take/review plan binding is stale")
            if review.take_sha256 != take.artifact_sha256:
                raise SequenceContinuityError("review take binding is stale")
            if review.anchor_take_id != plan.anchor_take_id or review.anchor_take_sha256 != plan.anchor_take_sha256:
                raise SequenceContinuityError("review anchor binding is stale")
            self._verify_plan_anchor_current(project_id, sequence, plan)
            self._verify_take_current(project_id, take)
            if any(
                item.shot_id == take.shot_id
                and item.take_id != take.take_id
                and item.status == "accepted"
                for item in sequence.takes
            ):
                raise SequenceContinuityError(
                    "shot already has an accepted take; rework it before accepting another"
                )
            accepted = replace(take, status="accepted")
            takes = tuple(
                accepted if item.take_id == take.take_id else item
                for item in sequence.takes
            )
            updated_sequence = replace(sequence, takes=takes)
            self._save(project_id, self._replace_sequence(state, updated_sequence))
            return accepted

    def reanchor(
        self, project_id: str, *, sequence_id: str, take_id: str
    ) -> SequenceRecord:
        with self.project_store._lock:
            state = self.load(project_id)
            sequence = state.sequence(sequence_id)
            take = sequence.take(take_id)
            if take.status != "accepted":
                raise SequenceContinuityError(
                    "sequence can only re-anchor to an accepted take"
                )
            self._verify_take_current(project_id, take)
            updated_sequence = replace(sequence, anchor_take_id=take.take_id)
            self._save(project_id, self._replace_sequence(state, updated_sequence))
            return updated_sequence

    def timeline_context(
        self,
        project_id: str,
        *,
        sequence_id: str,
        take_id: str,
        window_us: int = 1_500_000,
        samples: int = 3,
    ) -> dict[str, Any]:
        if isinstance(window_us, bool) or not isinstance(window_us, int) or window_us <= 0 or window_us > MAX_CONTEXT_WINDOW_US:
            raise SequenceContinuityError(
                f"window_us must be an integer in [1, {MAX_CONTEXT_WINDOW_US}]"
            )
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1 or samples > 8:
            raise SequenceContinuityError("samples must be an integer in [1, 8]")
        state = self.load(project_id)
        sequence = state.sequence(sequence_id)
        take = sequence.take(take_id)
        if take.status == "rejected":
            raise SequenceContinuityError(
                "rejected take cannot be used for continuity context"
            )
        plan = sequence.plan(take.shot_id)
        if take.plan_revision_sha256 != plan.revision_sha256:
            raise SequenceContinuityError("take plan binding is stale")
        self._verify_take_current(project_id, take)
        self._verify_plan_anchor_current(project_id, sequence, plan)
        candidate_reference, _, _ = self._resolve_reference(project_id, take.reference_id)
        candidate_duration = self._duration_us(candidate_reference)
        payload: dict[str, Any] = {
            "sequence_id": sequence.sequence_id,
            "shot_id": plan.shot_id,
            "plan_revision_sha256": plan.revision_sha256,
            "window_us": window_us,
            "candidate": self._context_media(
                take,
                candidate_duration,
                role="candidate",
                tail=False,
                window_us=window_us,
                samples=samples,
            ),
            "anchor": None,
            "locks": [item.to_dict() for item in plan.locks],
            "allowed_changes": [item.to_dict() for item in plan.allowed_changes],
            "review_targets": [item.to_dict() for item in plan.review_targets],
        }
        if plan.anchor_take_id is not None:
            anchor = sequence.take(plan.anchor_take_id)
            anchor_reference, _, _ = self._resolve_reference(project_id, anchor.reference_id)
            payload["anchor"] = self._context_media(
                anchor,
                self._duration_us(anchor_reference),
                role="anchor",
                tail=True,
                window_us=window_us,
                samples=samples,
            )
        return payload

    @staticmethod
    def _context_media(
        take: SequenceTake,
        duration_us: int,
        *,
        role: str,
        tail: bool,
        window_us: int,
        samples: int,
    ) -> dict[str, Any]:
        span = min(window_us, duration_us)
        start_us = max(0, duration_us - span) if tail else 0
        end_us = duration_us if tail else span
        if samples == 1:
            sample_times = [(start_us + end_us) // 2]
        else:
            sample_times = [
                start_us + ((end_us - start_us) * index // (samples - 1))
                for index in range(samples)
            ]
        return {
            "role": role,
            "take_id": take.take_id,
            "reference_id": take.reference_id,
            "reference_kind": take.reference_kind,
            "reference_path": take.reference_path,
            "sha256": take.artifact_sha256,
            "duration_us": duration_us,
            "window_start_us": start_us,
            "window_end_us": end_us,
            "sample_times_us": sample_times,
        }

    def _verify_plan_anchor_current(
        self, project_id: str, sequence: SequenceRecord, plan: SequenceShotPlan
    ) -> None:
        if plan.anchor_take_id is None:
            return
        anchor = sequence.take(plan.anchor_take_id)
        if anchor.status != "accepted":
            raise SequenceContinuityError("shot anchor is no longer accepted")
        if anchor.artifact_sha256 != plan.anchor_take_sha256:
            raise SequenceContinuityError("shot anchor identity changed")
        self._verify_take_current(project_id, anchor)

    def _verify_take_current(self, project_id: str, take: SequenceTake) -> None:
        reference, path, _ = self._resolve_reference(project_id, take.reference_id)
        if reference.path != take.reference_path:
            raise SequenceContinuityError(
                f"take {take.take_id!r} project reference path changed"
            )
        try:
            identity = verify_registered_media_bytes(path, reference.metadata)
        except MediaIntegrityError as exc:
            raise SequenceContinuityError(str(exc)) from exc
        if identity.sha256 != take.artifact_sha256 or identity.size_bytes != take.size_bytes:
            raise SequenceContinuityError(
                f"take {take.take_id!r} current bytes no longer match registered identity"
            )

    def _resolve_reference(
        self, project_id: str, reference_id: str
    ) -> tuple[ProjectReference, Any, str]:
        reference_id = _identifier(reference_id, field_name="reference_id")
        project = self.project_store.load_project(project_id)
        source_matches = [
            reference
            for reference in project.sources
            if reference.id == reference_id and reference.kind == "video"
        ]
        artifact_matches = [
            reference
            for reference in project.artifacts
            if reference.id == reference_id and reference.kind == "video"
        ]
        matches = [*source_matches, *artifact_matches]
        if len(matches) != 1:
            raise SequenceContinuityError(
                f"reference {reference_id!r} must identify exactly one project-owned video"
            )
        reference = matches[0]
        root = PurePosixPath(reference.path).parts[0]
        if root not in _MEDIA_ROOTS:
            raise SequenceContinuityError(
                f"video reference {reference_id!r} uses unsupported project root {root!r}"
            )
        path = self.project_store.resolve_project_file(
            project_id,
            reference.path,
            must_exist=True,
            allowed_roots=(root,),
        )
        return reference, path, "source" if source_matches else "artifact"

    @staticmethod
    def _duration_us(reference: ProjectReference) -> int:
        value = reference.metadata.get("duration_us")
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SequenceContinuityError(
                f"video reference {reference.id!r} requires positive duration_us metadata"
            )
        return value

    def _save(self, project_id: str, state: SequenceContinuityState) -> None:
        try:
            self.project_store._atomic_write_json(self._path(project_id), state.to_dict())
        except OSError as exc:
            raise ProjectStoreError("could not persist sequence continuity state") from exc

    @staticmethod
    def _replace_sequence(
        state: SequenceContinuityState, sequence: SequenceRecord
    ) -> SequenceContinuityState:
        return SequenceContinuityState(
            sequences=tuple(
                sequence if item.sequence_id == sequence.sequence_id else item
                for item in state.sequences
            )
        )
