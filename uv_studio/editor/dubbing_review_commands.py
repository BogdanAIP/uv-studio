"""Shared semantic commands for evidence-based dubbing review and acceptance."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from uv_studio.projects.dubbing_review import (
    AcceptedDubbingState,
    DubbingLoudnessEvidence,
    DubbingReviewError,
    DubbingReviewStore,
)
from uv_studio.projects.prepared_speech import PreparedSpeechError, PreparedSpeechStore
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

LoudnessMeasure = Callable[[str, str], Mapping[str, Any]]


class DubbingReviewCommandError(DubbingReviewError):
    """A dubbing review command cannot be applied to current project state."""


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
    """One Command API service; machine loudness evidence is never client supplied."""

    def __init__(self, project_store: ProjectStore, loudness_measure: LoudnessMeasure) -> None:
        self.project_store = project_store
        self.loudness_measure = loudness_measure
        self.prepared_speech = PreparedSpeechStore(project_store)
        self.reviews = DubbingReviewStore(project_store)

    @staticmethod
    def _new_review_id() -> str:
        return f"dreview_{uuid.uuid4().hex}"

    @staticmethod
    def _new_accepted_id() -> str:
        return f"dedit_{uuid.uuid4().hex}"

    def review_prepared_speech(
        self,
        project_id: str,
        command: ReviewPreparedSpeechCommand,
    ) -> DubbingReviewCommandResult:
        if not isinstance(command, ReviewPreparedSpeechCommand):
            raise DubbingReviewCommandError(
                "review_prepared_speech requires ReviewPreparedSpeechCommand"
            )
        try:
            take = self.prepared_speech.validate_project(project_id).get(command.take_id)
            raw = self.loudness_measure(project_id, take.audio_id)
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
        except ProjectNotFound:
            raise
        except (PreparedSpeechError, DubbingReviewError, ProjectStoreError) as exc:
            raise DubbingReviewCommandError(str(exc)) from exc
        return DubbingReviewCommandResult(
            command="review_prepared_speech",
            payload={"review": review.to_dict()},
        )

    def accept_dubbing_review(
        self,
        project_id: str,
        command: AcceptDubbingReviewCommand,
    ) -> DubbingReviewCommandResult:
        if not isinstance(command, AcceptDubbingReviewCommand):
            raise DubbingReviewCommandError(
                "accept_dubbing_review requires AcceptDubbingReviewCommand"
            )
        try:
            state: AcceptedDubbingState = self.reviews.accept_review(
                project_id,
                review_id=command.review_id,
                accepted_id=command.accepted_id or self._new_accepted_id(),
                composition_policy=command.composition_policy,
            )
            edit = next(item for item in state.edits if item.review_id == command.review_id)
        except ProjectNotFound:
            raise
        except (DubbingReviewError, PreparedSpeechError, ProjectStoreError) as exc:
            raise DubbingReviewCommandError(str(exc)) from exc
        return DubbingReviewCommandResult(
            command="accept_dubbing_review",
            payload={"accepted_dubbing": edit.to_dict()},
        )
