"""Semantic dubbing commands shared by GUI, scripts, AI and MCP."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from uv_studio.projects.dubbing import (
    DubbingError,
    DubbingStore,
    DubbingTranscript,
    DubbingTranslation,
    TranscriptSegment,
    TranslationSegment,
)
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.source_media import (
    ProjectSourceMediaStore,
    SourceMediaError,
    SourceMediaNotFound,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError


class DubbingCommandError(ProjectValidationError):
    """A semantic dubbing command is invalid for the current canonical project state."""


def _optional_identifier(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DubbingCommandError(f"{field_name} must be null or a non-empty identifier")
    from uv_studio.projects.models import validate_identifier

    try:
        return validate_identifier(value.strip(), field_name=field_name)
    except ProjectValidationError as exc:
        raise DubbingCommandError(str(exc)) from exc


def _source_sha256(metadata: dict[str, Any]) -> str:
    value = metadata.get("sha256")
    if not isinstance(value, str) or len(value) != 64:
        raise DubbingCommandError("registered source media is missing a valid sha256")
    return value


@dataclass(frozen=True)
class ImportTranscriptSegmentInput:
    segment_id: str
    start_us: int
    end_us: int
    text: str
    speaker_label: str | None = None
    confidence: float | None = None

    def to_domain(self) -> TranscriptSegment:
        try:
            return TranscriptSegment(
                segment_id=self.segment_id,
                start_us=self.start_us,
                end_us=self.end_us,
                text=self.text,
                speaker_label=self.speaker_label,
                confidence=self.confidence,
            )
        except DubbingError as exc:
            raise DubbingCommandError(str(exc)) from exc


@dataclass(frozen=True)
class ImportDubbingTranscriptCommand:
    source_id: str
    language: str
    start_us: int
    end_us: int
    segments: tuple[ImportTranscriptSegmentInput, ...]
    dubbing_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise DubbingCommandError("source_id must be a non-empty string")
        object.__setattr__(self, "source_id", self.source_id.strip())
        object.__setattr__(self, "dubbing_id", _optional_identifier(self.dubbing_id, field_name="dubbing_id"))
        segments = tuple(self.segments)
        if not segments or not all(isinstance(item, ImportTranscriptSegmentInput) for item in segments):
            raise DubbingCommandError("segments must contain at least one transcript segment")
        object.__setattr__(self, "segments", segments)


@dataclass(frozen=True)
class TranslationSegmentInput:
    segment_id: str
    text: str

    def to_domain(self) -> TranslationSegment:
        try:
            return TranslationSegment(segment_id=self.segment_id, text=self.text)
        except DubbingError as exc:
            raise DubbingCommandError(str(exc)) from exc


@dataclass(frozen=True)
class UpsertDubbingTranslationCommand:
    dubbing_id: str
    target_language: str
    segments: tuple[TranslationSegmentInput, ...]
    translation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dubbing_id, str) or not self.dubbing_id.strip():
            raise DubbingCommandError("dubbing_id must be a non-empty string")
        object.__setattr__(self, "dubbing_id", self.dubbing_id.strip())
        object.__setattr__(
            self,
            "translation_id",
            _optional_identifier(self.translation_id, field_name="translation_id"),
        )
        segments = tuple(self.segments)
        if not segments or not all(isinstance(item, TranslationSegmentInput) for item in segments):
            raise DubbingCommandError("segments must contain at least one translation segment")
        object.__setattr__(self, "segments", segments)


@dataclass(frozen=True)
class DubbingCommandResult:
    command: str
    dubbing_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "dubbing_id": self.dubbing_id,
            "payload": dict(self.payload),
        }


class DubbingCommandService:
    """Product mutation boundary for canonical transcript and translation state."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.source_media = ProjectSourceMediaStore(project_store)
        self.dubbing = DubbingStore(project_store)

    @staticmethod
    def _new_dubbing_id() -> str:
        return f"dub_{uuid.uuid4().hex}"

    @staticmethod
    def _new_translation_id() -> str:
        return f"translation_{uuid.uuid4().hex}"

    def _store_transcript(
        self,
        project_id: str,
        command: ImportDubbingTranscriptCommand,
        *,
        origin: str,
        command_name: str,
    ) -> DubbingCommandResult:
        if not isinstance(command, ImportDubbingTranscriptCommand):
            raise DubbingCommandError(f"{command_name} requires ImportDubbingTranscriptCommand")
        try:
            source = self.source_media.get(project_id, command.source_id)
            transcript = DubbingTranscript(
                dubbing_id=command.dubbing_id or self._new_dubbing_id(),
                source_id=source.id,
                source_sha256=_source_sha256(source.metadata),
                language=command.language,
                start_us=command.start_us,
                end_us=command.end_us,
                origin=origin,
                segments=tuple(item.to_domain() for item in command.segments),
            )
            state = self.dubbing.upsert_transcript(project_id, transcript)
            stored = state.get_transcript(transcript.dubbing_id)
        except (ProjectNotFound, SourceMediaNotFound):
            raise
        except (DubbingError, SourceMediaError, ProjectStoreError, ProjectValidationError) as exc:
            raise DubbingCommandError(str(exc)) from exc
        return DubbingCommandResult(
            command=command_name,
            dubbing_id=stored.dubbing_id,
            payload={"transcript": stored.to_dict(), "transcript_sha256": stored.digest},
        )

    def import_transcript(
        self,
        project_id: str,
        command: ImportDubbingTranscriptCommand,
    ) -> DubbingCommandResult:
        return self._store_transcript(
            project_id,
            command,
            origin="imported",
            command_name="import_dubbing_transcript",
        )

    def accept_asr_transcript(
        self,
        project_id: str,
        command: ImportDubbingTranscriptCommand,
    ) -> DubbingCommandResult:
        """Persist a reviewed ASR draft without trusting engine-side project identity."""

        return self._store_transcript(
            project_id,
            command,
            origin="asr",
            command_name="accept_asr_transcript",
        )

    def upsert_translation(
        self,
        project_id: str,
        command: UpsertDubbingTranslationCommand,
    ) -> DubbingCommandResult:
        if not isinstance(command, UpsertDubbingTranslationCommand):
            raise DubbingCommandError(
                "upsert_dubbing_translation requires UpsertDubbingTranslationCommand"
            )
        try:
            current = self.dubbing.validate_project(project_id)
            transcript = current.get_transcript(command.dubbing_id)
            translation = DubbingTranslation(
                translation_id=command.translation_id or self._new_translation_id(),
                dubbing_id=transcript.dubbing_id,
                transcript_sha256=transcript.digest,
                target_language=command.target_language,
                segments=tuple(item.to_domain() for item in command.segments),
            )
            state = self.dubbing.upsert_translation(project_id, translation)
            stored = state.get_translation(translation.translation_id)
        except (ProjectNotFound, SourceMediaNotFound):
            raise
        except DubbingError:
            raise
        except (SourceMediaError, ProjectStoreError, ProjectValidationError) as exc:
            raise DubbingCommandError(str(exc)) from exc
        return DubbingCommandResult(
            command="upsert_dubbing_translation",
            dubbing_id=stored.dubbing_id,
            payload={"translation": stored.to_dict()},
        )
