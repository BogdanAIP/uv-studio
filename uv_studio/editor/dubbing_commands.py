"""Semantic dubbing commands shared by GUI, scripts, AI and MCP."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from uv_studio.projects.dubbing import (
    DubbingError,
    DubbingStore,
    DubbingTranscript,
    DubbingTranscriptNotFound,
    DubbingTranslation,
    DubbingTranslationNotFound,
    TranscriptSegment,
    TranslationSegment,
)
from uv_studio.projects.media_integrity import MediaIntegrityError, verify_registered_media_bytes
from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.prepared_audio import (
    PreparedAudioError,
    PreparedAudioNotFound,
    ProjectPreparedAudioStore,
)
from uv_studio.projects.prepared_speech import (
    PreparedSpeechError,
    PreparedSpeechStore,
    PreparedSpeechTake,
    canonical_revision_sha256,
)
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


def _audio_sha256(metadata: dict[str, Any]) -> str:
    value = metadata.get("sha256")
    if not isinstance(value, str) or len(value) != 64:
        raise DubbingCommandError("registered prepared audio is missing a valid sha256")
    return value


def _audio_duration_us(metadata: dict[str, Any]) -> int:
    value = metadata.get("duration_us")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DubbingCommandError("registered prepared audio is missing a valid duration_us")
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
class AttachPreparedSpeechCommand:
    dubbing_id: str
    audio_id: str
    translation_id: str | None = None
    segment_id: str | None = None
    take_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("dubbing_id", "audio_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DubbingCommandError(f"{field_name} must be a non-empty identifier")
            object.__setattr__(self, field_name, value.strip())
        object.__setattr__(
            self,
            "translation_id",
            _optional_identifier(self.translation_id, field_name="translation_id"),
        )
        object.__setattr__(
            self,
            "segment_id",
            _optional_identifier(self.segment_id, field_name="segment_id"),
        )
        object.__setattr__(self, "take_id", _optional_identifier(self.take_id, field_name="take_id"))


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
    """Product mutation boundary for canonical dubbing workflow state."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.source_media = ProjectSourceMediaStore(project_store)
        self.prepared_audio = ProjectPreparedAudioStore(project_store)
        self.dubbing = DubbingStore(project_store)
        self.prepared_speech = PreparedSpeechStore(project_store)

    @staticmethod
    def _new_dubbing_id() -> str:
        return f"dub_{uuid.uuid4().hex}"

    @staticmethod
    def _new_translation_id() -> str:
        return f"translation_{uuid.uuid4().hex}"

    @staticmethod
    def _new_take_id() -> str:
        # Existing Stage 5 UI falls back to the last canonical take after refresh.
        # A z-prefixed fixed-width creation stamp keeps new takes after legacy random
        # IDs while remaining opaque identity; exact selection still remains a UI concern.
        return f"take_z{time.time_ns():020d}_{uuid.uuid4().hex}"

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
            with self.project_store._lock:
                source, _source_path = self.source_media.resolve_verified(project_id, command.source_id)
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
                current = self.dubbing.load(project_id)
                try:
                    previous = current.get_transcript(transcript.dubbing_id)
                except DubbingTranscriptNotFound:
                    previous = None
                if (
                    previous is not None
                    and previous.digest != transcript.digest
                    and self.prepared_speech.has_dubbing_bindings(project_id, transcript.dubbing_id)
                ):
                    raise DubbingCommandError(
                        "cannot change transcript while prepared speech takes are bound to its current revision"
                    )
                state = self.dubbing.upsert_transcript(project_id, transcript)
                stored = state.get_transcript(transcript.dubbing_id)
        except (ProjectNotFound, SourceMediaNotFound):
            raise
        except DubbingCommandError:
            raise
        except (
            DubbingError,
            PreparedSpeechError,
            SourceMediaError,
            ProjectStoreError,
            ProjectValidationError,
        ) as exc:
            raise DubbingCommandError(str(exc)) from exc
        return DubbingCommandResult(
            command=command_name,
            dubbing_id=stored.dubbing_id,
            payload={"transcript": stored.to_dict(), "transcript_sha256": stored.digest},
        )

    def import_transcript(self, project_id: str, command: ImportDubbingTranscriptCommand) -> DubbingCommandResult:
        return self._store_transcript(
            project_id,
            command,
            origin="imported",
            command_name="import_dubbing_transcript",
        )

    def accept_asr_transcript(self, project_id: str, command: ImportDubbingTranscriptCommand) -> DubbingCommandResult:
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
            with self.project_store._lock:
                current = self.dubbing.validate_project(project_id)
                transcript = current.get_transcript(command.dubbing_id)
                previous = None
                translation_id = command.translation_id
                if translation_id is not None:
                    try:
                        previous = current.get_translation(translation_id)
                    except DubbingTranslationNotFound as exc:
                        raise DubbingCommandError(
                            "translation_id can update only an existing translation"
                        ) from exc

                candidate = DubbingTranslation(
                    translation_id=translation_id or self._new_translation_id(),
                    dubbing_id=transcript.dubbing_id,
                    transcript_sha256=transcript.digest,
                    target_language=command.target_language,
                    segments=tuple(item.to_domain() for item in command.segments),
                )
                if previous is not None and (
                    previous.dubbing_id != candidate.dubbing_id
                    or previous.target_language != candidate.target_language
                ):
                    # Identity is immutable: a changed transcript/language target is a
                    # new translation, never a retargeting of the old translation ID.
                    previous = None
                    candidate = DubbingTranslation(
                        translation_id=self._new_translation_id(),
                        dubbing_id=transcript.dubbing_id,
                        transcript_sha256=transcript.digest,
                        target_language=command.target_language,
                        segments=tuple(item.to_domain() for item in command.segments),
                    )
                if (
                    previous is not None
                    and canonical_revision_sha256(previous.to_dict())
                    != canonical_revision_sha256(candidate.to_dict())
                    and self.prepared_speech.has_translation_bindings(
                        project_id, previous.translation_id
                    )
                ):
                    raise DubbingCommandError(
                        "cannot change translation while prepared speech takes are bound to its current revision"
                    )
                state = self.dubbing.upsert_translation(project_id, candidate)
                stored = state.get_translation(candidate.translation_id)
        except (ProjectNotFound, SourceMediaNotFound):
            raise
        except DubbingCommandError:
            raise
        except DubbingError:
            raise
        except (PreparedSpeechError, SourceMediaError, ProjectStoreError, ProjectValidationError) as exc:
            raise DubbingCommandError(str(exc)) from exc
        return DubbingCommandResult(
            command="upsert_dubbing_translation",
            dubbing_id=stored.dubbing_id,
            payload={"translation": stored.to_dict()},
        )

    def attach_prepared_speech(
        self,
        project_id: str,
        command: AttachPreparedSpeechCommand,
    ) -> DubbingCommandResult:
        if not isinstance(command, AttachPreparedSpeechCommand):
            raise DubbingCommandError("attach_prepared_speech requires AttachPreparedSpeechCommand")
        try:
            with self.project_store._lock:
                dubbing = self.dubbing.validate_project(project_id)
                transcript = dubbing.get_transcript(command.dubbing_id)
                if command.translation_id is None:
                    script_kind = "transcript"
                    script_id = transcript.dubbing_id
                    script_sha256 = transcript.digest
                else:
                    translation = dubbing.get_translation(command.translation_id)
                    if translation.dubbing_id != transcript.dubbing_id:
                        raise DubbingCommandError(
                            "prepared speech translation belongs to a different dubbing transcript"
                        )
                    script_kind = "translation"
                    script_id = translation.translation_id
                    script_sha256 = canonical_revision_sha256(translation.to_dict())

                audio, audio_path = self.prepared_audio.resolve(project_id, command.audio_id)
                try:
                    verify_registered_media_bytes(audio_path, audio.metadata)
                except MediaIntegrityError as exc:
                    raise DubbingCommandError(str(exc)) from exc
                origin = audio.metadata.get("origin")
                if origin not in {"imported", "recorded", "tts"}:
                    raise DubbingCommandError("registered prepared audio has invalid origin")
                take = PreparedSpeechTake(
                    take_id=command.take_id or self._new_take_id(),
                    dubbing_id=transcript.dubbing_id,
                    script_kind=script_kind,
                    script_id=script_id,
                    script_sha256=script_sha256,
                    audio_id=audio.id,
                    audio_sha256=_audio_sha256(audio.metadata),
                    duration_us=_audio_duration_us(audio.metadata),
                    origin=origin,
                    segment_id=command.segment_id,
                )
                state = self.prepared_speech.upsert(project_id, take)
                stored = state.get(take.take_id)
        except (ProjectNotFound, SourceMediaNotFound, PreparedAudioNotFound):
            raise
        except DubbingCommandError:
            raise
        except (
            DubbingError,
            PreparedAudioError,
            PreparedSpeechError,
            ProjectStoreError,
            ProjectValidationError,
        ) as exc:
            raise DubbingCommandError(str(exc)) from exc
        return DubbingCommandResult(
            command="attach_prepared_speech",
            dubbing_id=stored.dubbing_id,
            payload={"prepared_speech": stored.to_dict()},
        )
