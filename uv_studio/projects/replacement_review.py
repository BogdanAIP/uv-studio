"""Provider-neutral evidence-based replacement review gate for Stage 4B."""

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
from .edit_state import AcceptedRangeEdit, EditStateError, RangeEditState, RangeEditStateStore
from .media_ranges import ProjectMediaRange
from .models import ProjectValidationError, validate_identifier
from .replacement_candidate import (
    ReplacementCandidate,
    ReplacementCandidateError,
    ReplacementCandidateNotFound,
    ReplacementCandidateStore,
)
from .store import ProjectStore, ProjectStoreError

REPLACEMENT_REVIEW_SCHEMA_VERSION = 1
REPLACEMENT_REVIEW_PATH = "reviews/replacement-reviews.json"
REVIEW_VERDICTS = frozenset({"approved", "rejected", "needs_revision"})
REVIEW_OUTCOMES = frozenset({"pass", "fail", "uncertain"})
REVIEW_OBSERVATION_KINDS = frozenset({"observation", "inference"})
REVIEW_CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
REVIEW_EVIDENCE_KINDS = frozenset({"brief_evidence", "candidate_artifact"})
MAX_REVIEW_OBSERVATIONS = 64
MAX_REVIEW_ASSESSMENTS = 64
_HASH_CHUNK_BYTES = 1024 * 1024


class ReplacementReviewError(ProjectValidationError):
    """Invalid, stale or inconsistent replacement review state."""


class ReplacementReviewNotFound(ReplacementReviewError):
    pass


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise ReplacementReviewError(str(exc)) from exc


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise ReplacementReviewError(f"{field_name} must be a lowercase SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ReplacementReviewError(f"{field_name} must be a lowercase SHA-256 digest") from exc
    return value


def _text(value: Any, *, field_name: str, max_length: int = 4000) -> str:
    if not isinstance(value, str):
        raise ReplacementReviewError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ReplacementReviewError(f"{field_name} must not be empty")
    if len(normalized) > max_length:
        raise ReplacementReviewError(f"{field_name} must be <= {max_length} characters")
    return normalized


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    if unknown:
        raise ReplacementReviewError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    missing = allowed.difference(data)
    if missing:
        raise ReplacementReviewError(f"{kind} is missing fields: {sorted(missing)!r}")


def replacement_candidate_sha256(candidate: ReplacementCandidate) -> str:
    payload = json.dumps(
        candidate.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ReviewEvidenceReference:
    kind: str
    ref_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or self.kind not in REVIEW_EVIDENCE_KINDS:
            raise ReplacementReviewError(
                f"review evidence kind must be one of {sorted(REVIEW_EVIDENCE_KINDS)!r}"
            )
        object.__setattr__(
            self,
            "ref_id",
            _identifier(self.ref_id, field_name="review evidence ref_id"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "ref_id": self.ref_id}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReviewEvidenceReference":
        if not isinstance(data, Mapping):
            raise ReplacementReviewError("review evidence reference must be an object")
        allowed = {"kind", "ref_id"}
        _strict_fields(data, allowed=allowed, kind="review evidence reference")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ReplacementReviewObservation:
    observation_id: str
    kind: str
    statement: str
    confidence: str
    evidence: tuple[ReviewEvidenceReference, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _identifier(self.observation_id, field_name="review observation_id"),
        )
        if not isinstance(self.kind, str) or self.kind not in REVIEW_OBSERVATION_KINDS:
            raise ReplacementReviewError(
                f"review observation kind must be one of {sorted(REVIEW_OBSERVATION_KINDS)!r}"
            )
        object.__setattr__(
            self,
            "statement",
            _text(self.statement, field_name="review observation statement"),
        )
        if (
            not isinstance(self.confidence, str)
            or self.confidence not in REVIEW_CONFIDENCE_LEVELS
        ):
            raise ReplacementReviewError(
                "review observation confidence must be one of "
                f"{sorted(REVIEW_CONFIDENCE_LEVELS)!r}"
            )
        evidence = tuple(self.evidence)
        if not evidence or not all(
            isinstance(item, ReviewEvidenceReference) for item in evidence
        ):
            raise ReplacementReviewError("review observation must cite typed evidence")
        keys = [(item.kind, item.ref_id) for item in evidence]
        if len(keys) != len(set(keys)):
            raise ReplacementReviewError(
                "review observation evidence references must be unique"
            )
        object.__setattr__(self, "evidence", evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "kind": self.kind,
            "statement": self.statement,
            "confidence": self.confidence,
            "evidence": [item.to_dict() for item in self.evidence],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementReviewObservation":
        if not isinstance(data, Mapping):
            raise ReplacementReviewError(
                "replacement review observation must be an object"
            )
        allowed = {
            "observation_id",
            "kind",
            "statement",
            "confidence",
            "evidence",
        }
        _strict_fields(data, allowed=allowed, kind="replacement review observation")
        if not isinstance(data["evidence"], list):
            raise ReplacementReviewError(
                "review observation evidence must be a list"
            )
        return cls(
            observation_id=data["observation_id"],
            kind=data["kind"],
            statement=data["statement"],
            confidence=data["confidence"],
            evidence=tuple(
                ReviewEvidenceReference.from_dict(item) for item in data["evidence"]
            ),
        )


@dataclass(frozen=True)
class ReplacementReviewAssessment:
    target_id: str
    outcome: str
    observation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_id",
            _identifier(self.target_id, field_name="review target_id"),
        )
        if not isinstance(self.outcome, str) or self.outcome not in REVIEW_OUTCOMES:
            raise ReplacementReviewError(
                f"review outcome must be one of {sorted(REVIEW_OUTCOMES)!r}"
            )
        if not isinstance(self.observation_ids, (tuple, list)):
            raise ReplacementReviewError(
                "review assessment observation_ids must be a list"
            )
        observation_ids = tuple(
            _identifier(item, field_name="review assessment observation_id")
            for item in self.observation_ids
        )
        if not observation_ids:
            raise ReplacementReviewError(
                "review assessment must cite at least one observation"
            )
        if len(observation_ids) != len(set(observation_ids)):
            raise ReplacementReviewError(
                "review assessment observation_ids must be unique"
            )
        object.__setattr__(self, "observation_ids", observation_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "outcome": self.outcome,
            "observation_ids": list(self.observation_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementReviewAssessment":
        if not isinstance(data, Mapping):
            raise ReplacementReviewError(
                "replacement review assessment must be an object"
            )
        allowed = {"target_id", "outcome", "observation_ids"}
        _strict_fields(data, allowed=allowed, kind="replacement review assessment")
        if not isinstance(data["observation_ids"], list):
            raise ReplacementReviewError(
                "review assessment observation_ids must be a list"
            )
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class ReplacementReview:
    review_id: str
    candidate_id: str
    edit_id: str
    source_path: str
    start_us: int
    end_us: int
    plan_sha256: str
    candidate_sha256: str
    artifact_sha256: str
    verdict: str
    observations: tuple[ReplacementReviewObservation, ...]
    assessments: tuple[ReplacementReviewAssessment, ...]
    schema_version: int = REPLACEMENT_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != REPLACEMENT_REVIEW_SCHEMA_VERSION
        ):
            raise ReplacementReviewError(
                f"unsupported replacement review schema: {self.schema_version!r}"
            )
        object.__setattr__(
            self,
            "review_id",
            _identifier(self.review_id, field_name="review_id"),
        )
        object.__setattr__(
            self,
            "candidate_id",
            _identifier(self.candidate_id, field_name="candidate_id"),
        )
        object.__setattr__(
            self,
            "edit_id",
            _identifier(self.edit_id, field_name="edit_id"),
        )
        try:
            target = ProjectMediaRange(
                source_path=self.source_path,
                start_us=self.start_us,
                end_us=self.end_us,
            )
        except ProjectValidationError as exc:
            raise ReplacementReviewError(str(exc)) from exc
        object.__setattr__(self, "source_path", target.source_path)
        object.__setattr__(self, "start_us", target.start_us)
        object.__setattr__(self, "end_us", target.end_us)
        object.__setattr__(
            self,
            "plan_sha256",
            _sha256(self.plan_sha256, field_name="plan_sha256"),
        )
        object.__setattr__(
            self,
            "candidate_sha256",
            _sha256(self.candidate_sha256, field_name="candidate_sha256"),
        )
        object.__setattr__(
            self,
            "artifact_sha256",
            _sha256(self.artifact_sha256, field_name="artifact_sha256"),
        )
        if not isinstance(self.verdict, str) or self.verdict not in REVIEW_VERDICTS:
            raise ReplacementReviewError(
                f"review verdict must be one of {sorted(REVIEW_VERDICTS)!r}"
            )
        observations = tuple(self.observations)
        assessments = tuple(self.assessments)
        if not observations or not all(
            isinstance(item, ReplacementReviewObservation) for item in observations
        ):
            raise ReplacementReviewError("replacement review requires observations")
        if not assessments or not all(
            isinstance(item, ReplacementReviewAssessment) for item in assessments
        ):
            raise ReplacementReviewError("replacement review requires assessments")
        if len(observations) > MAX_REVIEW_OBSERVATIONS:
            raise ReplacementReviewError(
                f"replacement review may contain at most {MAX_REVIEW_OBSERVATIONS} observations"
            )
        if len(assessments) > MAX_REVIEW_ASSESSMENTS:
            raise ReplacementReviewError(
                f"replacement review may contain at most {MAX_REVIEW_ASSESSMENTS} assessments"
            )
        observation_ids = [item.observation_id for item in observations]
        target_ids = [item.target_id for item in assessments]
        if len(observation_ids) != len(set(observation_ids)):
            raise ReplacementReviewError("review observation IDs must be unique")
        if len(target_ids) != len(set(target_ids)):
            raise ReplacementReviewError("review target assessments must be unique")
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "assessments", assessments)

    @property
    def target_identity(self) -> tuple[str, str, int, int]:
        return (self.edit_id, self.source_path, self.start_us, self.end_us)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "candidate_id": self.candidate_id,
            "edit_id": self.edit_id,
            "source_path": self.source_path,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "plan_sha256": self.plan_sha256,
            "candidate_sha256": self.candidate_sha256,
            "artifact_sha256": self.artifact_sha256,
            "verdict": self.verdict,
            "observations": [item.to_dict() for item in self.observations],
            "assessments": [item.to_dict() for item in self.assessments],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementReview":
        if not isinstance(data, Mapping):
            raise ReplacementReviewError("replacement review must be an object")
        allowed = {
            "schema_version",
            "review_id",
            "candidate_id",
            "edit_id",
            "source_path",
            "start_us",
            "end_us",
            "plan_sha256",
            "candidate_sha256",
            "artifact_sha256",
            "verdict",
            "observations",
            "assessments",
        }
        _strict_fields(data, allowed=allowed, kind="replacement review")
        if not isinstance(data["observations"], list) or not isinstance(
            data["assessments"], list
        ):
            raise ReplacementReviewError(
                "review observations and assessments must be lists"
            )
        return cls(
            schema_version=data["schema_version"],
            review_id=data["review_id"],
            candidate_id=data["candidate_id"],
            edit_id=data["edit_id"],
            source_path=data["source_path"],
            start_us=data["start_us"],
            end_us=data["end_us"],
            plan_sha256=data["plan_sha256"],
            candidate_sha256=data["candidate_sha256"],
            artifact_sha256=data["artifact_sha256"],
            verdict=data["verdict"],
            observations=tuple(
                ReplacementReviewObservation.from_dict(item)
                for item in data["observations"]
            ),
            assessments=tuple(
                ReplacementReviewAssessment.from_dict(item)
                for item in data["assessments"]
            ),
        )


@dataclass(frozen=True)
class ReplacementReviewState:
    reviews: tuple[ReplacementReview, ...] = ()
    schema_version: int = REPLACEMENT_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != REPLACEMENT_REVIEW_SCHEMA_VERSION
        ):
            raise ReplacementReviewError(
                f"unsupported replacement review state schema: {self.schema_version!r}"
            )
        reviews = tuple(self.reviews)
        if not all(isinstance(item, ReplacementReview) for item in reviews):
            raise ReplacementReviewError(
                "reviews must contain ReplacementReview values"
            )
        ids = [item.review_id for item in reviews]
        if len(ids) != len(set(ids)):
            raise ReplacementReviewError("review_id values must be unique")
        object.__setattr__(
            self,
            "reviews",
            tuple(sorted(reviews, key=lambda item: item.review_id)),
        )

    def get(self, review_id: str) -> ReplacementReview:
        normalized = _identifier(review_id, field_name="review_id")
        for review in self.reviews:
            if review.review_id == normalized:
                return review
        raise ReplacementReviewNotFound(normalized)

    def add(self, review: ReplacementReview) -> "ReplacementReviewState":
        if not isinstance(review, ReplacementReview):
            raise ReplacementReviewError("add requires ReplacementReview")
        return ReplacementReviewState(reviews=(*self.reviews, review))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "reviews": [item.to_dict() for item in self.reviews],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplacementReviewState":
        if not isinstance(data, Mapping):
            raise ReplacementReviewError(
                "replacement review state must be an object"
            )
        allowed = {"schema_version", "reviews"}
        _strict_fields(data, allowed=allowed, kind="replacement review state")
        if not isinstance(data["reviews"], list):
            raise ReplacementReviewError(
                "replacement review state reviews must be a list"
            )
        return cls(
            schema_version=data["schema_version"],
            reviews=tuple(
                ReplacementReview.from_dict(item) for item in data["reviews"]
            ),
        )


class ReplacementReviewStore:
    """Atomic review history and exact approved-review acceptance boundary."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _state_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                REPLACEMENT_REVIEW_PATH,
                must_exist=False,
                allowed_roots=("reviews",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise ReplacementReviewError(str(exc)) from exc

    def load(self, project_id: str) -> ReplacementReviewState:
        path = self._state_path(project_id)
        if not path.exists():
            return ReplacementReviewState()
        if not path.is_file() or path.is_symlink():
            raise ReplacementReviewError(
                "replacement review state path must be a regular project file"
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReplacementReviewError(
                "replacement review state is malformed JSON"
            ) from exc
        except OSError as exc:
            raise ReplacementReviewError(
                "replacement review state could not be read"
            ) from exc
        return ReplacementReviewState.from_dict(data)

    def _write(
        self,
        project_id: str,
        state: ReplacementReviewState,
    ) -> ReplacementReviewState:
        self.project_store._atomic_write_json(
            self._state_path(project_id), state.to_dict()
        )
        return state

    def _current_candidate_and_brief(
        self,
        project_id: str,
        candidate_id: str,
    ) -> tuple[ReplacementCandidate, RangeContinuityBrief]:
        try:
            candidate = ReplacementCandidateStore(
                self.project_store
            ).validate_candidate(project_id, candidate_id)
        except (
            ReplacementCandidateError,
            ReplacementCandidateNotFound,
            ProjectStoreError,
        ) as exc:
            raise ReplacementReviewError(
                "replacement review requires a current valid ReplacementCandidate: "
                f"{exc}"
            ) from exc
        if candidate.stage != "full":
            raise ReplacementReviewError(
                "final replacement review requires a full candidate"
            )
        try:
            brief = RangeContinuityBriefStore(
                self.project_store
            ).validate_project(project_id).get(candidate.edit_id)
        except (
            ContinuityBriefError,
            ContinuityBriefNotFound,
            ProjectStoreError,
        ) as exc:
            raise ReplacementReviewError(
                "replacement review requires a current valid RangeContinuityBrief: "
                f"{exc}"
            ) from exc
        if candidate.target_identity != brief.target_identity:
            raise ReplacementReviewError(
                "candidate target no longer matches the current continuity brief"
            )
        if not brief.review_targets:
            raise ReplacementReviewError(
                "current continuity brief must define at least one review target "
                "before final review"
            )
        return candidate, brief

    def _candidate_artifact_sha256(
        self,
        project_id: str,
        candidate: ReplacementCandidate,
    ) -> str:
        try:
            path = self.project_store.resolve_project_file(
                project_id,
                candidate.artifact_path,
                must_exist=True,
                allowed_roots=("artifacts",),
            )
            if not path.is_file() or path.is_symlink():
                raise ReplacementReviewError(
                    "reviewed candidate artifact must be a regular project file"
                )
            before = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                while chunk := handle.read(_HASH_CHUNK_BYTES):
                    digest.update(chunk)
            after = path.stat()
        except ReplacementReviewError:
            raise
        except (OSError, ProjectStoreError, ProjectValidationError) as exc:
            raise ReplacementReviewError(
                f"reviewed candidate artifact could not be hashed: {exc}"
            ) from exc
        before_signature = (before.st_size, before.st_mtime_ns)
        after_signature = (after.st_size, after.st_mtime_ns)
        if before_signature != after_signature:
            raise ReplacementReviewError(
                "reviewed candidate artifact changed while its digest was being computed"
            )
        return digest.hexdigest()

    def create_review(
        self,
        project_id: str,
        *,
        review_id: str,
        candidate_id: str,
        verdict: str,
        observations: tuple[ReplacementReviewObservation, ...],
        assessments: tuple[ReplacementReviewAssessment, ...],
    ) -> ReplacementReviewState:
        with self.project_store._lock:
            candidate, brief = self._current_candidate_and_brief(
                project_id, candidate_id
            )
            review = ReplacementReview(
                review_id=review_id,
                candidate_id=candidate.candidate_id,
                edit_id=candidate.edit_id,
                source_path=candidate.source_path,
                start_us=candidate.start_us,
                end_us=candidate.end_us,
                plan_sha256=candidate.plan_sha256,
                candidate_sha256=replacement_candidate_sha256(candidate),
                artifact_sha256=self._candidate_artifact_sha256(
                    project_id, candidate
                ),
                verdict=verdict,
                observations=observations,
                assessments=assessments,
            )
            self._validate_review_against_current(
                project_id, review, candidate, brief
            )
            current = self.load(project_id)
            return self._write(project_id, current.add(review))

    def validate_review(
        self,
        project_id: str,
        review_id: str,
    ) -> ReplacementReview:
        review = self.load(project_id).get(review_id)
        candidate, brief = self._current_candidate_and_brief(
            project_id, review.candidate_id
        )
        self._validate_review_against_current(
            project_id, review, candidate, brief
        )
        return review

    def accept_review(
        self,
        project_id: str,
        review_id: str,
    ) -> RangeEditState:
        with self.project_store._lock:
            review = self.load(project_id).get(review_id)
            candidate, brief = self._current_candidate_and_brief(
                project_id, review.candidate_id
            )
            self._validate_review_against_current(
                project_id, review, candidate, brief
            )
            if review.verdict != "approved":
                raise ReplacementReviewError(
                    "only an approved current replacement review can be accepted"
                )
            edit = AcceptedRangeEdit(
                edit_id=candidate.edit_id,
                source_path=candidate.source_path,
                start_us=candidate.start_us,
                end_us=candidate.end_us,
                replacement_path=candidate.artifact_path,
            )
            try:
                return RangeEditStateStore(self.project_store).accept(
                    project_id, edit
                )
            except EditStateError as exc:
                raise ReplacementReviewError(
                    f"approved replacement review could not be accepted: {exc}"
                ) from exc

    def _validate_review_against_current(
        self,
        project_id: str,
        review: ReplacementReview,
        candidate: ReplacementCandidate,
        brief: RangeContinuityBrief,
    ) -> None:
        if review.candidate_id != candidate.candidate_id:
            raise ReplacementReviewError(
                "review candidate_id does not match current candidate"
            )
        if review.target_identity != candidate.target_identity:
            raise ReplacementReviewError(
                "review target no longer matches current candidate"
            )
        if review.plan_sha256 != candidate.plan_sha256:
            raise ReplacementReviewError(
                "review is stale because the approved plan changed"
            )
        if review.candidate_sha256 != replacement_candidate_sha256(candidate):
            raise ReplacementReviewError(
                "review is stale because the candidate changed"
            )
        current_artifact_sha256 = self._candidate_artifact_sha256(
            project_id, candidate
        )
        if review.artifact_sha256 != current_artifact_sha256:
            raise ReplacementReviewError(
                "review is stale because the candidate artifact bytes changed"
            )
        if review.target_identity != brief.target_identity:
            raise ReplacementReviewError(
                "review target no longer matches current continuity brief"
            )

        expected_targets = {
            item.target_id: item for item in brief.review_targets
        }
        actual_targets = {item.target_id for item in review.assessments}
        if actual_targets != set(expected_targets):
            missing = sorted(set(expected_targets).difference(actual_targets))
            extra = sorted(actual_targets.difference(expected_targets))
            raise ReplacementReviewError(
                "review assessments must exactly match current review targets "
                f"(missing={missing!r}, extra={extra!r})"
            )

        brief_evidence = {item.evidence_id for item in brief.evidence}
        observations = {
            item.observation_id: item for item in review.observations
        }
        for observation in review.observations:
            for evidence in observation.evidence:
                if (
                    evidence.kind == "brief_evidence"
                    and evidence.ref_id not in brief_evidence
                ):
                    raise ReplacementReviewError(
                        f"review observation {observation.observation_id!r} "
                        "references unknown Brief evidence "
                        f"{evidence.ref_id!r}"
                    )
                if (
                    evidence.kind == "candidate_artifact"
                    and evidence.ref_id != candidate.artifact_id
                ):
                    raise ReplacementReviewError(
                        f"review observation {observation.observation_id!r} "
                        "references a different candidate artifact"
                    )

        referenced_observations: set[str] = set()
        for assessment in review.assessments:
            missing_observations = set(assessment.observation_ids).difference(
                observations
            )
            if missing_observations:
                raise ReplacementReviewError(
                    f"review target {assessment.target_id!r} references unknown "
                    f"observations: {sorted(missing_observations)!r}"
                )
            referenced_observations.update(assessment.observation_ids)
            candidate_grounded = any(
                any(
                    evidence.kind == "candidate_artifact"
                    and evidence.ref_id == candidate.artifact_id
                    for evidence in observations[observation_id].evidence
                )
                for observation_id in assessment.observation_ids
            )
            if not candidate_grounded:
                raise ReplacementReviewError(
                    f"review target {assessment.target_id!r} must cite at least "
                    "one observation of the exact candidate artifact"
                )
        orphan_observations = set(observations).difference(
            referenced_observations
        )
        if orphan_observations:
            raise ReplacementReviewError(
                "replacement review contains observations not used by any "
                f"assessment: {sorted(orphan_observations)!r}"
            )

        outcomes = {
            item.target_id: item.outcome for item in review.assessments
        }
        required_targets = [
            item.target_id for item in brief.review_targets if item.required
        ]
        has_fail = any(outcome == "fail" for outcome in outcomes.values())
        has_uncertain = any(
            outcome == "uncertain" for outcome in outcomes.values()
        )
        required_pass = all(
            outcomes[target_id] == "pass" for target_id in required_targets
        )
        if review.verdict == "approved":
            if not required_pass or has_fail:
                raise ReplacementReviewError(
                    "approved review requires every required target to pass "
                    "and no target to fail"
                )
        elif review.verdict == "rejected":
            if not has_fail:
                raise ReplacementReviewError(
                    "rejected review requires at least one failed target"
                )
        elif review.verdict == "needs_revision":
            if not (has_fail or has_uncertain):
                raise ReplacementReviewError(
                    "needs_revision review requires at least one failed or "
                    "uncertain target"
                )
