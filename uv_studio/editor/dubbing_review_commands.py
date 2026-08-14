"""Shared semantic commands for evidence-based dubbing review and acceptance."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from uv_studio.projects.dubbing import DubbingError, DubbingStore
from uv_studio.projects.dubbing_review import (
    AcceptedDubbingState,
    DubbingLoudnessEvidence,
    DubbingReview,
    DubbingReviewError,
    DubbingReviewStore,
)
from uv_studio.projects.dubbing_review_current import CurrentReviewError, CurrentReviewStore
from uv_studio.projects.media_integrity import MediaIntegrityError, verify_registered_media_bytes
from uv_studio.projects.prepared_audio import PreparedAudioError, ProjectPreparedAudioStore
from uv_studio.projects.prepared_speech import PreparedSpeechError, PreparedSpeechStore
from uv_studio.projects.source_media import ProjectSourceMediaStore, SourceMediaError
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

LoudnessMeasure = Callable[[str, str], Mapping[str, Any]]


class DubbingReviewCommandError(DubbingReviewError):
    pass


@dataclass(frozen=True)
class ReviewPreparedSpeechCommand:
    take_id: str
    verdict: str
    content_fidelity_confirmed: bool
    synchronization_confirmed: bool
    note: str | None = None
    review_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.take_id, str) or not self.take_id.strip():
            raise DubbingReviewCommandError("take_id must be a non-empty identifier")
        object.__setattr__(self, "take_id", self.take_id.strip())
        if self.review_id is not None:
            if not isinstance(self.review_id, str) or not self.review_id.strip():
                raise DubbingReviewCommandError("review_id must be null or a non-empty identifier")
            object.__setattr__(self, "review_id", self.review_id.strip())
        if not isinstance(self.content_fidelity_confirmed, bool):
            raise DubbingReviewCommandError("content_fidelity_confirmed must be boolean")
        if not isinstance(self.synchronization_confirmed, bool):
            raise DubbingReviewCommandError("synchronization_confirmed must be boolean")


@dataclass(frozen=True)
class AcceptDubbingReviewCommand:
    review_id: str
    composition_policy: str
    accepted_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("review_id", "composition_policy"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DubbingReviewCommandError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        if self.accepted_id is not None:
            if not isinstance(self.accepted_id, str) or not self.accepted_id.strip():
                raise DubbingReviewCommandError("accepted_id must be null or a non-empty identifier")
            object.__setattr__(self, "accepted_id", self.accepted_id.strip())


@dataclass(frozen=True)
class DubbingReviewCommandResult:
    command: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"command": self.command, "payload": dict(self.payload)}


class DubbingReviewCommandService:
    """One Command API service with current-byte evidence and explicit current Review."""

    def __init__(self, project_store: ProjectStore, loudness_measure: LoudnessMeasure) -> None:
        self.project_store = project_store
        self.loudness_measure = loudness_measure
        self.prepared_speech = PreparedSpeechStore(project_store)
        self.prepared_audio = ProjectPreparedAudioStore(project_store)
        self.dubbing = DubbingStore(project_store)
        self.source_media = ProjectSourceMediaStore(project_store)
        self.reviews = DubbingReviewStore(project_store)
        self.current_reviews = CurrentReviewStore(project_store)

    @staticmethod
    def _new_review_id() -> str:
        return f"dreview_{uuid.uuid4().hex}"

    @staticmethod
    def _new_accepted_id() -> str:
        return f"dedit_{uuid.uuid4().hex}"

    @staticmethod
    def _ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
        return start_a < end_b and end_a > start_b

    @classmethod
    def _reject_overlapping_acceptance(cls, review: DubbingReview, accepted: AcceptedDubbingState) -> None:
        for existing in accepted.edits:
            if existing.review_id == review.review_id:
                raise DubbingReviewCommandError(f"dubbing review {review.review_id!r} is already accepted")
            if existing.source_id != review.source_id:
                continue
            if cls._ranges_overlap(
                review.target_start_us,
                review.target_end_us,
                existing.target_start_us,
                existing.target_end_us,
            ):
                raise DubbingReviewCommandError(
                    "accepted dubbing ranges for one source must not overlap: "
                    f"existing={existing.accepted_id!r}, review={review.review_id!r}"
                )

    def _verify_take_media(self, project_id: str, take_id: str) -> None:
        take = self.prepared_speech.validate_project(project_id).get(take_id)
        transcript = self.dubbing.validate_project(project_id).get_transcript(take.dubbing_id)
        source, _source_path = self.source_media.resolve_verified(project_id, transcript.source_id)
        if source.metadata.get("sha256") != transcript.source_sha256:
            raise DubbingReviewCommandError("dubbing source identity no longer matches transcript")
        audio, audio_path = self.prepared_audio.resolve(project_id, take.audio_id)
        verify_registered_media_bytes(audio_path, audio.metadata)
        if audio.metadata.get("sha256") != take.audio_sha256:
            raise DubbingReviewCommandError("prepared speech audio identity no longer matches take")

    def review_prepared_speech(
        self,
        project_id: str,
        command: ReviewPreparedSpeechCommand,
    ) -> DubbingReviewCommandResult:
        if not isinstance(command, ReviewPreparedSpeechCommand):
            raise DubbingReviewCommandError("review_prepared_speech requires ReviewPreparedSpeechCommand")
        try:
            with self.project_store._lock:
                self._verify_take_media(project_id, command.take_id)
                take = self.prepared_speech.validate_project(project_id).get(command.take_id)
                raw = self.loudness_measure(project_id, take.audio_id)
                # Detect external mutation while FFmpeg measured the audio.
                self._verify_take_media(project_id, command.take_id)
                loudness = DubbingLoudnessEvidence(
                    audio_id=raw.get("audio_id"),
                    audio_sha256=raw.get("audio_sha256"),
                    duration_us=raw.get("duration_us"),
                    measurable=raw.get("measurable"),
                    integrated_lufs=raw.get("integrated_lufs"),
                    true_peak_dbtp=raw.get("true_peak_dbtp"),
                    loudness_range_lu=raw.get("loudness_range_lu"),
                    threshold_lufs=raw.get("threshold_lufs"),
                )
                review_id = command.review_id or self._new_review_id()
                state = self.reviews.create_review(
                    project_id,
                    review_id=review_id,
                    take_id=take.take_id,
                    loudness=loudness,
                    content_fidelity_confirmed=command.content_fidelity_confirmed,
                    synchronization_confirmed=command.synchronization_confirmed,
                    verdict=command.verdict,
                    note=command.note,
                )
                review = state.get(review_id)
                self.current_reviews.set_current(project_id, take.take_id, review.review_id)
        except ProjectNotFound:
            raise
        except (
            PreparedSpeechError,
            PreparedAudioError,
            SourceMediaError,
            MediaIntegrityError,
            DubbingError,
            DubbingReviewError,
            CurrentReviewError,
            ProjectStoreError,
        ) as exc:
            raise DubbingReviewCommandError(str(exc)) from exc
        return DubbingReviewCommandResult(
            command="review_prepared_speech",
            payload={"review": review.to_dict(), "current_review_id": review.review_id},
        )

    def accept_dubbing_review(
        self,
        project_id: str,
        command: AcceptDubbingReviewCommand,
    ) -> DubbingReviewCommandResult:
        if not isinstance(command, AcceptDubbingReviewCommand):
            raise DubbingReviewCommandError("accept_dubbing_review requires AcceptDubbingReviewCommand")
        try:
            with self.project_store._lock:
                history = self.reviews.load_reviews(project_id)
                review = history.get(command.review_id)
                current_id = self.current_reviews.resolve_current(
                    project_id, review.take_id, history.reviews
                )
                if current_id is None:
                    raise DubbingReviewCommandError(
                        "review history has ambiguous legacy ordering; create a new Review before acceptance"
                    )
                if current_id != review.review_id:
                    raise DubbingReviewCommandError(
                        "only the explicit current Review for a prepared speech take can be accepted"
                    )
                self._verify_take_media(project_id, review.take_id)
                review = self.reviews.validate_review(project_id, command.review_id)
                accepted = self.reviews.load_accepted(project_id, validate_current=True)
                self._reject_overlapping_acceptance(review, accepted)
                state = self.reviews.accept_review(
                    project_id,
                    review_id=command.review_id,
                    accepted_id=command.accepted_id or self._new_accepted_id(),
                    composition_policy=command.composition_policy,
                )
                edit = next(item for item in state.edits if item.review_id == command.review_id)
        except ProjectNotFound:
            raise
        except (
            DubbingReviewError,
            CurrentReviewError,
            PreparedSpeechError,
            PreparedAudioError,
            SourceMediaError,
            MediaIntegrityError,
            DubbingError,
            ProjectStoreError,
        ) as exc:
            raise DubbingReviewCommandError(str(exc)) from exc
        return DubbingReviewCommandResult(
            command="accept_dubbing_review",
            payload={"accepted_dubbing": edit.to_dict()},
        )
