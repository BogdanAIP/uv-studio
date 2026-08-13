"""Evidence-based Stage 5 dubbing review and immutable acceptance state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .dubbing import DubbingError, DubbingStore, DubbingTranscript
from .models import ProjectValidationError, validate_identifier
from .prepared_speech import (
    PreparedSpeechError,
    PreparedSpeechStore,
    PreparedSpeechTake,
    canonical_revision_sha256,
)
from .store import ProjectStore, ProjectStoreError

DUBBING_REVIEW_SCHEMA_VERSION = 1
DUBBING_REVIEW_PATH = "reviews/dubbing-reviews.json"
ACCEPTED_DUBBING_SCHEMA_VERSION = 1
ACCEPTED_DUBBING_PATH = "timeline/accepted-dubbing.json"
DUBBING_REVIEW_VERDICTS = frozenset({"approved", "rejected", "needs_revision"})
DUBBING_COMPOSITION_POLICIES = frozenset(
    {
        "replace_source_audio_range",
        "duck_source_mix",
        "replace_dialogue_preserve_background",
    }
)
DUBBING_TIMING_OVERFLOW_TOLERANCE_US = 100_000
DUBBING_MAX_TRUE_PEAK_DBTP = -1.0
MAX_REVIEW_NOTE_LENGTH = 4000


class DubbingReviewError(ProjectValidationError):
    """Invalid, stale or inconsistent dubbing review state."""


class DubbingReviewNotFound(DubbingReviewError):
    pass


class AcceptedDubbingEditNotFound(DubbingReviewError):
    pass


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise DubbingReviewError(str(exc)) from exc


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise DubbingReviewError(f"{field_name} must be a lowercase SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise DubbingReviewError(f"{field_name} must be a lowercase SHA-256 hex digest") from exc
    return value


def _microseconds(value: Any, *, field_name: str, positive: bool = False) -> int:
    minimum = 1 if positive else 0
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        qualifier = "positive" if positive else "non-negative"
        raise DubbingReviewError(f"{field_name} must be a {qualifier} integer microsecond value")
    return value


def _finite_number(value: Any, *, field_name: str, nullable: bool = False) -> float | None:
    import math

    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DubbingReviewError(f"{field_name} must be a finite number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise DubbingReviewError(f"{field_name} must be a finite number")
    return parsed


def _note(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DubbingReviewError("review note must be null or a string")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_REVIEW_NOTE_LENGTH:
        raise DubbingReviewError(
            f"review note must be <= {MAX_REVIEW_NOTE_LENGTH} characters"
        )
    return normalized


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    missing = allowed.difference(data)
    if unknown:
        raise DubbingReviewError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    if missing:
        raise DubbingReviewError(f"{kind} is missing fields: {sorted(missing)!r}")


def prepared_speech_take_sha256(take: PreparedSpeechTake) -> str:
    return canonical_revision_sha256(take.to_dict())


@dataclass(frozen=True)
class DubbingLoudnessEvidence:
    audio_id: str
    audio_sha256: str
    duration_us: int
    measurable: bool
    integrated_lufs: float | None
    true_peak_dbtp: float | None
    loudness_range_lu: float | None
    threshold_lufs: float | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "audio_id", _identifier(self.audio_id, field_name="audio_id"))
        object.__setattr__(
            self,
            "audio_sha256",
            _sha256(self.audio_sha256, field_name="audio_sha256"),
        )
        object.__setattr__(
            self,
            "duration_us",
            _microseconds(self.duration_us, field_name="duration_us", positive=True),
        )
        if not isinstance(self.measurable, bool):
            raise DubbingReviewError("measurable must be boolean")
        for field_name in (
            "integrated_lufs",
            "true_peak_dbtp",
            "loudness_range_lu",
            "threshold_lufs",
        ):
            object.__setattr__(
                self,
                field_name,
                _finite_number(
                    getattr(self, field_name), field_name=field_name, nullable=True
                ),
            )
        if self.measurable and (
            self.integrated_lufs is None or self.true_peak_dbtp is None
        ):
            raise DubbingReviewError(
                "measurable loudness evidence requires integrated_lufs and true_peak_dbtp"
            )

    @property
    def audio_safety_pass(self) -> bool:
        return bool(
            self.measurable
            and self.true_peak_dbtp is not None
            and self.true_peak_dbtp <= DUBBING_MAX_TRUE_PEAK_DBTP
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_id": self.audio_id,
            "audio_sha256": self.audio_sha256,
            "duration_us": self.duration_us,
            "measurable": self.measurable,
            "integrated_lufs": self.integrated_lufs,
            "true_peak_dbtp": self.true_peak_dbtp,
            "loudness_range_lu": self.loudness_range_lu,
            "threshold_lufs": self.threshold_lufs,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingLoudnessEvidence":
        if not isinstance(data, Mapping):
            raise DubbingReviewError("loudness evidence must be an object")
        allowed = {
            "audio_id",
            "audio_sha256",
            "duration_us",
            "measurable",
            "integrated_lufs",
            "true_peak_dbtp",
            "loudness_range_lu",
            "threshold_lufs",
        }
        _strict_fields(data, allowed=allowed, kind="loudness evidence")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class DubbingReview:
    review_id: str
    take_id: str
    take_sha256: str
    dubbing_id: str
    source_id: str
    source_sha256: str
    script_kind: str
    script_id: str
    script_sha256: str
    audio_id: str
    audio_sha256: str
    segment_id: str | None
    target_start_us: int
    target_end_us: int
    audio_duration_us: int
    timing_delta_us: int
    timing_pass: bool
    loudness: DubbingLoudnessEvidence
    audio_safety_pass: bool
    content_fidelity_confirmed: bool
    synchronization_confirmed: bool
    verdict: str
    note: str | None = None
    schema_version: int = DUBBING_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DUBBING_REVIEW_SCHEMA_VERSION or isinstance(
            self.schema_version, bool
        ):
            raise DubbingReviewError(
                f"unsupported dubbing review schema: {self.schema_version!r}"
            )
        for field_name in (
            "review_id",
            "take_id",
            "dubbing_id",
            "source_id",
            "script_id",
            "audio_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier(getattr(self, field_name), field_name=field_name),
            )
        for field_name in (
            "take_sha256",
            "source_sha256",
            "script_sha256",
            "audio_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _sha256(getattr(self, field_name), field_name=field_name),
            )
        if self.script_kind not in {"transcript", "translation"}:
            raise DubbingReviewError("script_kind must be transcript or translation")
        if self.segment_id is not None:
            object.__setattr__(
                self,
                "segment_id",
                _identifier(self.segment_id, field_name="segment_id"),
            )
        start = _microseconds(self.target_start_us, field_name="target_start_us")
        end = _microseconds(self.target_end_us, field_name="target_end_us", positive=True)
        if end <= start:
            raise DubbingReviewError("target_end_us must be greater than target_start_us")
        object.__setattr__(self, "target_start_us", start)
        object.__setattr__(self, "target_end_us", end)
        object.__setattr__(
            self,
            "audio_duration_us",
            _microseconds(self.audio_duration_us, field_name="audio_duration_us", positive=True),
        )
        if isinstance(self.timing_delta_us, bool) or not isinstance(self.timing_delta_us, int):
            raise DubbingReviewError("timing_delta_us must be an integer")
        expected_delta = self.audio_duration_us - (self.target_end_us - self.target_start_us)
        if self.timing_delta_us != expected_delta:
            raise DubbingReviewError("timing_delta_us does not match target/audio duration")
        expected_timing_pass = expected_delta <= DUBBING_TIMING_OVERFLOW_TOLERANCE_US
        if self.timing_pass is not expected_timing_pass:
            raise DubbingReviewError("timing_pass does not match Stage 5 timing policy")
        if not isinstance(self.loudness, DubbingLoudnessEvidence):
            raise DubbingReviewError("loudness must be DubbingLoudnessEvidence")
        if self.loudness.audio_id != self.audio_id:
            raise DubbingReviewError("loudness evidence references a different audio_id")
        if self.loudness.audio_sha256 != self.audio_sha256:
            raise DubbingReviewError("loudness evidence references a different audio revision")
        if self.loudness.duration_us != self.audio_duration_us:
            raise DubbingReviewError("loudness evidence duration does not match prepared speech")
        if self.audio_safety_pass is not self.loudness.audio_safety_pass:
            raise DubbingReviewError("audio_safety_pass does not match loudness evidence")
        for field_name in (
            "content_fidelity_confirmed",
            "synchronization_confirmed",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise DubbingReviewError(f"{field_name} must be boolean")
        if self.verdict not in DUBBING_REVIEW_VERDICTS:
            raise DubbingReviewError(
                f"verdict must be one of {sorted(DUBBING_REVIEW_VERDICTS)!r}"
            )
        object.__setattr__(self, "note", _note(self.note))
        if self.verdict == "approved" and not (
            self.timing_pass
            and self.audio_safety_pass
            and self.content_fidelity_confirmed
            and self.synchronization_confirmed
        ):
            raise DubbingReviewError(
                "approved dubbing review requires timing/audio checks and explicit content/sync confirmation"
            )

    @property
    def target_duration_us(self) -> int:
        return self.target_end_us - self.target_start_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "take_id": self.take_id,
            "take_sha256": self.take_sha256,
            "dubbing_id": self.dubbing_id,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "script_kind": self.script_kind,
            "script_id": self.script_id,
            "script_sha256": self.script_sha256,
            "audio_id": self.audio_id,
            "audio_sha256": self.audio_sha256,
            "segment_id": self.segment_id,
            "target_start_us": self.target_start_us,
            "target_end_us": self.target_end_us,
            "audio_duration_us": self.audio_duration_us,
            "timing_delta_us": self.timing_delta_us,
            "timing_pass": self.timing_pass,
            "loudness": self.loudness.to_dict(),
            "audio_safety_pass": self.audio_safety_pass,
            "content_fidelity_confirmed": self.content_fidelity_confirmed,
            "synchronization_confirmed": self.synchronization_confirmed,
            "verdict": self.verdict,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingReview":
        if not isinstance(data, Mapping):
            raise DubbingReviewError("dubbing review must be an object")
        allowed = {
            "schema_version",
            "review_id",
            "take_id",
            "take_sha256",
            "dubbing_id",
            "source_id",
            "source_sha256",
            "script_kind",
            "script_id",
            "script_sha256",
            "audio_id",
            "audio_sha256",
            "segment_id",
            "target_start_us",
            "target_end_us",
            "audio_duration_us",
            "timing_delta_us",
            "timing_pass",
            "loudness",
            "audio_safety_pass",
            "content_fidelity_confirmed",
            "synchronization_confirmed",
            "verdict",
            "note",
        }
        _strict_fields(data, allowed=allowed, kind="dubbing review")
        return cls(
            **{key: data[key] for key in allowed if key != "loudness"},
            loudness=DubbingLoudnessEvidence.from_dict(data["loudness"]),
        )


@dataclass(frozen=True)
class DubbingReviewState:
    reviews: tuple[DubbingReview, ...] = ()
    schema_version: int = DUBBING_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DUBBING_REVIEW_SCHEMA_VERSION or isinstance(
            self.schema_version, bool
        ):
            raise DubbingReviewError(
                f"unsupported dubbing review state schema: {self.schema_version!r}"
            )
        reviews = tuple(self.reviews)
        if not all(isinstance(item, DubbingReview) for item in reviews):
            raise DubbingReviewError("reviews must contain DubbingReview values")
        ids = [item.review_id for item in reviews]
        if len(ids) != len(set(ids)):
            raise DubbingReviewError("dubbing review_id values must be unique")
        object.__setattr__(self, "reviews", tuple(sorted(reviews, key=lambda item: item.review_id)))

    def add(self, review: DubbingReview) -> "DubbingReviewState":
        return DubbingReviewState(reviews=(*self.reviews, review))

    def get(self, review_id: str) -> DubbingReview:
        normalized = _identifier(review_id, field_name="review_id")
        for item in self.reviews:
            if item.review_id == normalized:
                return item
        raise DubbingReviewNotFound(normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "reviews": [item.to_dict() for item in self.reviews],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingReviewState":
        if not isinstance(data, Mapping):
            raise DubbingReviewError("dubbing review state must be an object")
        allowed = {"schema_version", "reviews"}
        _strict_fields(data, allowed=allowed, kind="dubbing review state")
        if not isinstance(data["reviews"], list):
            raise DubbingReviewError("dubbing review state reviews must be a list")
        return cls(
            schema_version=data["schema_version"],
            reviews=tuple(DubbingReview.from_dict(item) for item in data["reviews"]),
        )


@dataclass(frozen=True)
class AcceptedDubbingEdit:
    accepted_id: str
    review_id: str
    take_id: str
    take_sha256: str
    dubbing_id: str
    source_id: str
    source_sha256: str
    target_start_us: int
    target_end_us: int
    script_kind: str
    script_id: str
    script_sha256: str
    audio_id: str
    audio_sha256: str
    segment_id: str | None
    composition_policy: str
    schema_version: int = ACCEPTED_DUBBING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACCEPTED_DUBBING_SCHEMA_VERSION or isinstance(
            self.schema_version, bool
        ):
            raise DubbingReviewError(
                f"unsupported accepted dubbing schema: {self.schema_version!r}"
            )
        for field_name in (
            "accepted_id",
            "review_id",
            "take_id",
            "dubbing_id",
            "source_id",
            "script_id",
            "audio_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier(getattr(self, field_name), field_name=field_name),
            )
        for field_name in (
            "take_sha256",
            "source_sha256",
            "script_sha256",
            "audio_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _sha256(getattr(self, field_name), field_name=field_name),
            )
        start = _microseconds(self.target_start_us, field_name="target_start_us")
        end = _microseconds(self.target_end_us, field_name="target_end_us", positive=True)
        if end <= start:
            raise DubbingReviewError("accepted target_end_us must be greater than target_start_us")
        object.__setattr__(self, "target_start_us", start)
        object.__setattr__(self, "target_end_us", end)
        if self.script_kind not in {"transcript", "translation"}:
            raise DubbingReviewError("accepted script_kind must be transcript or translation")
        if self.segment_id is not None:
            object.__setattr__(self, "segment_id", _identifier(self.segment_id, field_name="segment_id"))
        if self.composition_policy not in DUBBING_COMPOSITION_POLICIES:
            raise DubbingReviewError(
                f"composition_policy must be one of {sorted(DUBBING_COMPOSITION_POLICIES)!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "accepted_id": self.accepted_id,
            "review_id": self.review_id,
            "take_id": self.take_id,
            "take_sha256": self.take_sha256,
            "dubbing_id": self.dubbing_id,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "target_start_us": self.target_start_us,
            "target_end_us": self.target_end_us,
            "script_kind": self.script_kind,
            "script_id": self.script_id,
            "script_sha256": self.script_sha256,
            "audio_id": self.audio_id,
            "audio_sha256": self.audio_sha256,
            "segment_id": self.segment_id,
            "composition_policy": self.composition_policy,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AcceptedDubbingEdit":
        if not isinstance(data, Mapping):
            raise DubbingReviewError("accepted dubbing edit must be an object")
        allowed = {
            "schema_version",
            "accepted_id",
            "review_id",
            "take_id",
            "take_sha256",
            "dubbing_id",
            "source_id",
            "source_sha256",
            "target_start_us",
            "target_end_us",
            "script_kind",
            "script_id",
            "script_sha256",
            "audio_id",
            "audio_sha256",
            "segment_id",
            "composition_policy",
        }
        _strict_fields(data, allowed=allowed, kind="accepted dubbing edit")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class AcceptedDubbingState:
    edits: tuple[AcceptedDubbingEdit, ...] = ()
    schema_version: int = ACCEPTED_DUBBING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACCEPTED_DUBBING_SCHEMA_VERSION or isinstance(
            self.schema_version, bool
        ):
            raise DubbingReviewError(
                f"unsupported accepted dubbing state schema: {self.schema_version!r}"
            )
        edits = tuple(self.edits)
        if not all(isinstance(item, AcceptedDubbingEdit) for item in edits):
            raise DubbingReviewError("edits must contain AcceptedDubbingEdit values")
        ids = [item.accepted_id for item in edits]
        reviews = [item.review_id for item in edits]
        takes = [item.take_id for item in edits]
        if len(ids) != len(set(ids)):
            raise DubbingReviewError("accepted dubbing IDs must be unique")
        if len(reviews) != len(set(reviews)):
            raise DubbingReviewError("a dubbing review may be accepted only once")
        if len(takes) != len(set(takes)):
            raise DubbingReviewError("a prepared speech take may be accepted only once")
        object.__setattr__(self, "edits", tuple(sorted(edits, key=lambda item: item.accepted_id)))

    def add(self, edit: AcceptedDubbingEdit) -> "AcceptedDubbingState":
        return AcceptedDubbingState(edits=(*self.edits, edit))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "edits": [item.to_dict() for item in self.edits],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AcceptedDubbingState":
        if not isinstance(data, Mapping):
            raise DubbingReviewError("accepted dubbing state must be an object")
        allowed = {"schema_version", "edits"}
        _strict_fields(data, allowed=allowed, kind="accepted dubbing state")
        if not isinstance(data["edits"], list):
            raise DubbingReviewError("accepted dubbing edits must be a list")
        return cls(
            schema_version=data["schema_version"],
            edits=tuple(AcceptedDubbingEdit.from_dict(item) for item in data["edits"]),
        )


class DubbingReviewStore:
    """Atomic review history and exact-current acceptance boundary."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.dubbing = DubbingStore(project_store)
        self.prepared_speech = PreparedSpeechStore(project_store)

    def _review_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                DUBBING_REVIEW_PATH,
                must_exist=False,
                allowed_roots=("reviews",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise DubbingReviewError(str(exc)) from exc

    def _accepted_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                ACCEPTED_DUBBING_PATH,
                must_exist=False,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise DubbingReviewError(str(exc)) from exc

    def load_reviews(self, project_id: str) -> DubbingReviewState:
        self.project_store.load_project(project_id)
        path = self._review_path(project_id)
        if not path.exists():
            return DubbingReviewState()
        if not path.is_file() or path.is_symlink():
            raise DubbingReviewError("dubbing review state must be a regular project file")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DubbingReviewError("dubbing review state is malformed JSON") from exc
        except OSError as exc:
            raise DubbingReviewError("dubbing review state could not be read") from exc
        return DubbingReviewState.from_dict(payload)

    def load_accepted(self, project_id: str, *, validate_current: bool = False) -> AcceptedDubbingState:
        self.project_store.load_project(project_id)
        path = self._accepted_path(project_id)
        if not path.exists():
            return AcceptedDubbingState()
        if not path.is_file() or path.is_symlink():
            raise DubbingReviewError("accepted dubbing state must be a regular project file")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DubbingReviewError("accepted dubbing state is malformed JSON") from exc
        except OSError as exc:
            raise DubbingReviewError("accepted dubbing state could not be read") from exc
        state = AcceptedDubbingState.from_dict(payload)
        if validate_current:
            for edit in state.edits:
                review = self.validate_review(project_id, edit.review_id)
                if review.verdict != "approved":
                    raise DubbingReviewError("accepted dubbing edit no longer has an approved review")
                self._validate_accepted_matches_review(edit, review)
        return state

    def _write_reviews(self, project_id: str, state: DubbingReviewState) -> DubbingReviewState:
        self.project_store._atomic_write_json(self._review_path(project_id), state.to_dict())
        return state

    def _write_accepted(self, project_id: str, state: AcceptedDubbingState) -> AcceptedDubbingState:
        self.project_store._atomic_write_json(self._accepted_path(project_id), state.to_dict())
        return state

    @staticmethod
    def _target_range(transcript: DubbingTranscript, take: PreparedSpeechTake) -> tuple[int, int]:
        if take.segment_id is None:
            return transcript.start_us, transcript.end_us
        for segment in transcript.segments:
            if segment.segment_id == take.segment_id:
                return segment.start_us, segment.end_us
        raise DubbingReviewError(
            f"prepared speech take {take.take_id!r} references a missing target segment"
        )

    def _current_take_context(
        self,
        project_id: str,
        take_id: str,
    ) -> tuple[PreparedSpeechTake, DubbingTranscript, int, int]:
        try:
            take = self.prepared_speech.validate_project(project_id).get(take_id)
            transcript = self.dubbing.validate_project(project_id).get_transcript(take.dubbing_id)
        except (PreparedSpeechError, DubbingError) as exc:
            raise DubbingReviewError(
                f"dubbing review requires current prepared speech and script state: {exc}"
            ) from exc
        start_us, end_us = self._target_range(transcript, take)
        return take, transcript, start_us, end_us

    def create_review(
        self,
        project_id: str,
        *,
        review_id: str,
        take_id: str,
        loudness: DubbingLoudnessEvidence,
        content_fidelity_confirmed: bool,
        synchronization_confirmed: bool,
        verdict: str,
        note: str | None = None,
    ) -> DubbingReviewState:
        with self.project_store._lock:
            take, transcript, start_us, end_us = self._current_take_context(project_id, take_id)
            if loudness.audio_id != take.audio_id or loudness.audio_sha256 != take.audio_sha256:
                raise DubbingReviewError("loudness evidence does not match the current prepared speech audio")
            if loudness.duration_us != take.duration_us:
                raise DubbingReviewError("loudness evidence duration does not match the current prepared speech")
            timing_delta_us = take.duration_us - (end_us - start_us)
            review = DubbingReview(
                review_id=review_id,
                take_id=take.take_id,
                take_sha256=prepared_speech_take_sha256(take),
                dubbing_id=take.dubbing_id,
                source_id=transcript.source_id,
                source_sha256=transcript.source_sha256,
                script_kind=take.script_kind,
                script_id=take.script_id,
                script_sha256=take.script_sha256,
                audio_id=take.audio_id,
                audio_sha256=take.audio_sha256,
                segment_id=take.segment_id,
                target_start_us=start_us,
                target_end_us=end_us,
                audio_duration_us=take.duration_us,
                timing_delta_us=timing_delta_us,
                timing_pass=timing_delta_us <= DUBBING_TIMING_OVERFLOW_TOLERANCE_US,
                loudness=loudness,
                audio_safety_pass=loudness.audio_safety_pass,
                content_fidelity_confirmed=content_fidelity_confirmed,
                synchronization_confirmed=synchronization_confirmed,
                verdict=verdict,
                note=note,
            )
            self._validate_review_against_current(project_id, review)
            current = self.load_reviews(project_id)
            return self._write_reviews(project_id, current.add(review))

    def _validate_review_against_current(self, project_id: str, review: DubbingReview) -> None:
        take, transcript, start_us, end_us = self._current_take_context(project_id, review.take_id)
        if review.take_sha256 != prepared_speech_take_sha256(take):
            raise DubbingReviewError("review is stale because the prepared speech take changed")
        if review.dubbing_id != take.dubbing_id:
            raise DubbingReviewError("review dubbing_id no longer matches the prepared speech take")
        if review.source_id != transcript.source_id or review.source_sha256 != transcript.source_sha256:
            raise DubbingReviewError("review is stale because source media changed")
        if (
            review.script_kind != take.script_kind
            or review.script_id != take.script_id
            or review.script_sha256 != take.script_sha256
        ):
            raise DubbingReviewError("review is stale because the reviewed script changed")
        if review.audio_id != take.audio_id or review.audio_sha256 != take.audio_sha256:
            raise DubbingReviewError("review is stale because the reviewed audio changed")
        if review.audio_duration_us != take.duration_us:
            raise DubbingReviewError("review is stale because the reviewed audio duration changed")
        if review.segment_id != take.segment_id:
            raise DubbingReviewError("review target segment no longer matches the prepared speech take")
        if (review.target_start_us, review.target_end_us) != (start_us, end_us):
            raise DubbingReviewError("review is stale because target timing changed")
        if review.loudness.audio_id != take.audio_id or review.loudness.audio_sha256 != take.audio_sha256:
            raise DubbingReviewError("review loudness evidence is stale for the current audio")

    def validate_review(self, project_id: str, review_id: str) -> DubbingReview:
        review = self.load_reviews(project_id).get(review_id)
        self._validate_review_against_current(project_id, review)
        return review

    @staticmethod
    def _validate_accepted_matches_review(edit: AcceptedDubbingEdit, review: DubbingReview) -> None:
        expected = {
            "review_id": review.review_id,
            "take_id": review.take_id,
            "take_sha256": review.take_sha256,
            "dubbing_id": review.dubbing_id,
            "source_id": review.source_id,
            "source_sha256": review.source_sha256,
            "target_start_us": review.target_start_us,
            "target_end_us": review.target_end_us,
            "script_kind": review.script_kind,
            "script_id": review.script_id,
            "script_sha256": review.script_sha256,
            "audio_id": review.audio_id,
            "audio_sha256": review.audio_sha256,
            "segment_id": review.segment_id,
        }
        mismatches = [key for key, value in expected.items() if getattr(edit, key) != value]
        if mismatches:
            raise DubbingReviewError(
                f"accepted dubbing edit no longer matches its review: {sorted(mismatches)!r}"
            )

    def accept_review(
        self,
        project_id: str,
        *,
        review_id: str,
        accepted_id: str,
        composition_policy: str,
    ) -> AcceptedDubbingState:
        with self.project_store._lock:
            review = self.validate_review(project_id, review_id)
            if review.verdict != "approved":
                raise DubbingReviewError("only a current approved dubbing review can be accepted")
            edit = AcceptedDubbingEdit(
                accepted_id=accepted_id,
                review_id=review.review_id,
                take_id=review.take_id,
                take_sha256=review.take_sha256,
                dubbing_id=review.dubbing_id,
                source_id=review.source_id,
                source_sha256=review.source_sha256,
                target_start_us=review.target_start_us,
                target_end_us=review.target_end_us,
                script_kind=review.script_kind,
                script_id=review.script_id,
                script_sha256=review.script_sha256,
                audio_id=review.audio_id,
                audio_sha256=review.audio_sha256,
                segment_id=review.segment_id,
                composition_policy=composition_policy,
            )
            current = self.load_accepted(project_id, validate_current=True)
            return self._write_accepted(project_id, current.add(edit))
