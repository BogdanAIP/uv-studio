"""Shared semantic command for accepting provider-neutral forced-alignment drafts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from uv_studio.projects.dubbing import DubbingError, DubbingStore, DubbingTranslationNotFound
from uv_studio.projects.dubbing_alignment import (
    DubbingAlignment,
    DubbingAlignmentError,
    DubbingAlignmentMark,
    DubbingAlignmentStore,
)
from uv_studio.projects.prepared_speech import (
    PreparedSpeechError,
    PreparedSpeechStore,
    canonical_revision_sha256,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError


class DubbingAlignmentCommandError(DubbingAlignmentError):
    """An alignment draft cannot be accepted into current canonical project state."""


@dataclass(frozen=True)
class AlignmentMarkInput:
    mark_id: str
    unit: str
    text: str
    audio_start_us: int
    audio_end_us: int
    confidence: float | None = None

    def to_domain(self) -> DubbingAlignmentMark:
        try:
            return DubbingAlignmentMark(
                mark_id=self.mark_id,
                unit=self.unit,
                text=self.text,
                audio_start_us=self.audio_start_us,
                audio_end_us=self.audio_end_us,
                confidence=self.confidence,
            )
        except DubbingAlignmentError as exc:
            raise DubbingAlignmentCommandError(str(exc)) from exc


@dataclass(frozen=True)
class AcceptDubbingAlignmentCommand:
    take_id: str
    marks: tuple[AlignmentMarkInput, ...]
    alignment_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.take_id, str) or not self.take_id.strip():
            raise DubbingAlignmentCommandError("take_id must be a non-empty identifier")
        object.__setattr__(self, "take_id", self.take_id.strip())
        marks = tuple(self.marks)
        if not marks or not all(isinstance(item, AlignmentMarkInput) for item in marks):
            raise DubbingAlignmentCommandError("marks must contain at least one typed alignment mark")
        object.__setattr__(self, "marks", marks)
        if self.alignment_id is not None:
            if not isinstance(self.alignment_id, str) or not self.alignment_id.strip():
                raise DubbingAlignmentCommandError(
                    "alignment_id must be null or a non-empty identifier"
                )
            object.__setattr__(self, "alignment_id", self.alignment_id.strip())


@dataclass(frozen=True)
class DubbingAlignmentCommandResult:
    command: str
    payload: dict

    def to_dict(self) -> dict:
        return {"command": self.command, "payload": dict(self.payload)}


class DubbingAlignmentCommandService:
    """Accept alignment marks while deriving every revision/range binding server-side."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.prepared_speech = PreparedSpeechStore(project_store)
        self.dubbing = DubbingStore(project_store)
        self.alignments = DubbingAlignmentStore(project_store)

    @staticmethod
    def _new_alignment_id() -> str:
        return f"align_{uuid.uuid4().hex}"

    def accept_alignment(
        self,
        project_id: str,
        command: AcceptDubbingAlignmentCommand,
    ) -> DubbingAlignmentCommandResult:
        if not isinstance(command, AcceptDubbingAlignmentCommand):
            raise DubbingAlignmentCommandError(
                "accept_dubbing_alignment requires AcceptDubbingAlignmentCommand"
            )
        try:
            with self.project_store._lock:
                take = self.prepared_speech.validate_project(project_id).get(command.take_id)
                state = self.dubbing.validate_project(project_id)
                transcript = state.get_transcript(take.dubbing_id)
                if take.segment_id is None:
                    target_start_us, target_end_us = transcript.start_us, transcript.end_us
                else:
                    segment = next(
                        (item for item in transcript.segments if item.segment_id == take.segment_id),
                        None,
                    )
                    if segment is None:
                        raise DubbingAlignmentCommandError(
                            "prepared speech segment no longer exists in current transcript"
                        )
                    target_start_us, target_end_us = segment.start_us, segment.end_us
                language = transcript.language
                if take.script_kind == "translation":
                    try:
                        translation = state.get_translation(take.script_id)
                    except DubbingTranslationNotFound as exc:
                        raise DubbingAlignmentCommandError(
                            "prepared speech translation no longer exists"
                        ) from exc
                    language = translation.target_language
                alignment = DubbingAlignment(
                    alignment_id=command.alignment_id or self._new_alignment_id(),
                    take_id=take.take_id,
                    take_sha256=canonical_revision_sha256(take.to_dict()),
                    dubbing_id=take.dubbing_id,
                    script_kind=take.script_kind,
                    script_id=take.script_id,
                    script_sha256=take.script_sha256,
                    audio_id=take.audio_id,
                    audio_sha256=take.audio_sha256,
                    language=language,
                    segment_id=take.segment_id,
                    target_start_us=target_start_us,
                    target_end_us=target_end_us,
                    marks=tuple(item.to_domain() for item in command.marks),
                )
                stored_state = self.alignments.upsert(project_id, alignment)
                stored = stored_state.for_take(take.take_id)
                if stored is None:
                    raise DubbingAlignmentCommandError("accepted alignment was not persisted")
        except ProjectNotFound:
            raise
        except DubbingAlignmentCommandError:
            raise
        except (
            DubbingAlignmentError,
            PreparedSpeechError,
            DubbingError,
            ProjectStoreError,
        ) as exc:
            raise DubbingAlignmentCommandError(str(exc)) from exc
        return DubbingAlignmentCommandResult(
            command="accept_dubbing_alignment",
            payload={"alignment": stored.to_dict()},
        )
