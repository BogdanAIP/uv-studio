"""Typed provider-neutral transcript and translation state for dubbing workflows."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .models import ProjectValidationError, validate_identifier
from .source_media import ProjectSourceMediaStore, SourceMediaError, SourceMediaNotFound
from .store import ProjectStore, ProjectStoreError

DUBBING_SCHEMA_VERSION = 1
DUBBING_STATE_PATH = "timeline/dubbing-state.json"
MAX_DUBBING_SEGMENTS = 100_000
MAX_SEGMENT_TEXT = 8_000
MAX_SPEAKER_LABEL = 128
MAX_LANGUAGE_TAG = 64
_TRANSCRIPT_ORIGINS = frozenset({"imported", "asr"})
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")


class DubbingError(ProjectValidationError):
    """Invalid, stale or inconsistent canonical dubbing state."""


class DubbingTranscriptNotFound(DubbingError):
    pass


class DubbingTranslationNotFound(DubbingError):
    pass


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    missing = allowed.difference(data)
    if unknown:
        raise DubbingError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    if missing:
        raise DubbingError(f"{kind} is missing fields: {sorted(missing)!r}")


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise DubbingError(str(exc)) from exc


def _text(value: Any, *, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise DubbingError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise DubbingError(f"{field_name} must not be empty")
    if len(normalized) > max_length:
        raise DubbingError(f"{field_name} must be <= {max_length} characters")
    return normalized


def _optional_text(value: Any, *, field_name: str, max_length: int) -> str | None:
    if value is None:
        return None
    return _text(value, field_name=field_name, max_length=max_length)


def _language(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise DubbingError(f"{field_name} must be a language tag string")
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_LANGUAGE_TAG or not _LANGUAGE_RE.fullmatch(normalized):
        raise DubbingError(
            f"{field_name} must be a portable language tag such as 'en', 'ru' or 'pt-BR'"
        )
    return normalized.lower()


def _positive_or_zero_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DubbingError(f"{field_name} must be a non-negative integer microsecond value")
    return value


def _positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DubbingError(f"{field_name} must be a positive integer microsecond value")
    return value


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise DubbingError(f"{field_name} must be a lowercase SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise DubbingError(f"{field_name} must be a lowercase SHA-256 hex digest") from exc
    return value


def _confidence(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DubbingError("confidence must be null or a number between 0 and 1")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0 or parsed > 1.0:
        raise DubbingError("confidence must be null or a finite number between 0 and 1")
    return parsed


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class TranscriptSegment:
    segment_id: str
    start_us: int
    end_us: int
    text: str
    speaker_label: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "segment_id", _identifier(self.segment_id, field_name="segment_id"))
        start_us = _positive_or_zero_int(self.start_us, field_name="start_us")
        end_us = _positive_int(self.end_us, field_name="end_us")
        if end_us <= start_us:
            raise DubbingError("segment end_us must be greater than start_us")
        object.__setattr__(self, "start_us", start_us)
        object.__setattr__(self, "end_us", end_us)
        object.__setattr__(self, "text", _text(self.text, field_name="text", max_length=MAX_SEGMENT_TEXT))
        object.__setattr__(
            self,
            "speaker_label",
            _optional_text(
                self.speaker_label,
                field_name="speaker_label",
                max_length=MAX_SPEAKER_LABEL,
            ),
        )
        object.__setattr__(self, "confidence", _confidence(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "text": self.text,
            "speaker_label": self.speaker_label,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TranscriptSegment":
        if not isinstance(data, Mapping):
            raise DubbingError("transcript segment must be an object")
        allowed = {"segment_id", "start_us", "end_us", "text", "speaker_label", "confidence"}
        _strict_fields(data, allowed=allowed, kind="transcript segment")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class DubbingTranscript:
    dubbing_id: str
    source_id: str
    source_sha256: str
    language: str
    start_us: int
    end_us: int
    origin: str
    segments: tuple[TranscriptSegment, ...]
    schema_version: int = DUBBING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DUBBING_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise DubbingError(f"unsupported dubbing transcript schema: {self.schema_version!r}")
        object.__setattr__(self, "dubbing_id", _identifier(self.dubbing_id, field_name="dubbing_id"))
        object.__setattr__(self, "source_id", _identifier(self.source_id, field_name="source_id"))
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, field_name="source_sha256"))
        object.__setattr__(self, "language", _language(self.language, field_name="language"))
        start_us = _positive_or_zero_int(self.start_us, field_name="start_us")
        end_us = _positive_int(self.end_us, field_name="end_us")
        if end_us <= start_us:
            raise DubbingError("transcript end_us must be greater than start_us")
        object.__setattr__(self, "start_us", start_us)
        object.__setattr__(self, "end_us", end_us)
        if self.origin not in _TRANSCRIPT_ORIGINS:
            raise DubbingError(f"origin must be one of {sorted(_TRANSCRIPT_ORIGINS)!r}")
        segments = tuple(self.segments)
        if not segments:
            raise DubbingError("transcript must contain at least one segment")
        if len(segments) > MAX_DUBBING_SEGMENTS:
            raise DubbingError(f"transcript may contain at most {MAX_DUBBING_SEGMENTS} segments")
        if not all(isinstance(item, TranscriptSegment) for item in segments):
            raise DubbingError("segments must contain TranscriptSegment values")
        ids = [item.segment_id for item in segments]
        if len(ids) != len(set(ids)):
            raise DubbingError("transcript segment_id values must be unique")
        ordered = tuple(sorted(segments, key=lambda item: (item.start_us, item.end_us, item.segment_id)))
        previous_end = start_us
        for segment in ordered:
            if segment.start_us < start_us or segment.end_us > end_us:
                raise DubbingError(
                    f"segment {segment.segment_id!r} must stay inside the transcript source range"
                )
            if segment.start_us < previous_end:
                raise DubbingError("transcript segments must not overlap")
            previous_end = segment.end_us
        object.__setattr__(self, "segments", ordered)

    @property
    def digest(self) -> str:
        return _canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dubbing_id": self.dubbing_id,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "language": self.language,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "origin": self.origin,
            "segments": [item.to_dict() for item in self.segments],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingTranscript":
        if not isinstance(data, Mapping):
            raise DubbingError("dubbing transcript must be an object")
        allowed = {
            "schema_version",
            "dubbing_id",
            "source_id",
            "source_sha256",
            "language",
            "start_us",
            "end_us",
            "origin",
            "segments",
        }
        _strict_fields(data, allowed=allowed, kind="dubbing transcript")
        if not isinstance(data["segments"], list):
            raise DubbingError("segments must be a list")
        return cls(
            schema_version=data["schema_version"],
            dubbing_id=data["dubbing_id"],
            source_id=data["source_id"],
            source_sha256=data["source_sha256"],
            language=data["language"],
            start_us=data["start_us"],
            end_us=data["end_us"],
            origin=data["origin"],
            segments=tuple(TranscriptSegment.from_dict(item) for item in data["segments"]),
        )


@dataclass(frozen=True)
class TranslationSegment:
    segment_id: str
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "segment_id", _identifier(self.segment_id, field_name="segment_id"))
        object.__setattr__(self, "text", _text(self.text, field_name="text", max_length=MAX_SEGMENT_TEXT))

    def to_dict(self) -> dict[str, Any]:
        return {"segment_id": self.segment_id, "text": self.text}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TranslationSegment":
        if not isinstance(data, Mapping):
            raise DubbingError("translation segment must be an object")
        allowed = {"segment_id", "text"}
        _strict_fields(data, allowed=allowed, kind="translation segment")
        return cls(segment_id=data["segment_id"], text=data["text"])


@dataclass(frozen=True)
class DubbingTranslation:
    translation_id: str
    dubbing_id: str
    transcript_sha256: str
    target_language: str
    segments: tuple[TranslationSegment, ...]
    schema_version: int = DUBBING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DUBBING_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise DubbingError(f"unsupported dubbing translation schema: {self.schema_version!r}")
        object.__setattr__(self, "translation_id", _identifier(self.translation_id, field_name="translation_id"))
        object.__setattr__(self, "dubbing_id", _identifier(self.dubbing_id, field_name="dubbing_id"))
        object.__setattr__(
            self,
            "transcript_sha256",
            _sha256(self.transcript_sha256, field_name="transcript_sha256"),
        )
        object.__setattr__(
            self,
            "target_language",
            _language(self.target_language, field_name="target_language"),
        )
        segments = tuple(self.segments)
        if not segments:
            raise DubbingError("translation must contain at least one segment")
        if len(segments) > MAX_DUBBING_SEGMENTS:
            raise DubbingError(f"translation may contain at most {MAX_DUBBING_SEGMENTS} segments")
        if not all(isinstance(item, TranslationSegment) for item in segments):
            raise DubbingError("segments must contain TranslationSegment values")
        ids = [item.segment_id for item in segments]
        if len(ids) != len(set(ids)):
            raise DubbingError("translation segment_id values must be unique")
        object.__setattr__(self, "segments", tuple(sorted(segments, key=lambda item: item.segment_id)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "translation_id": self.translation_id,
            "dubbing_id": self.dubbing_id,
            "transcript_sha256": self.transcript_sha256,
            "target_language": self.target_language,
            "segments": [item.to_dict() for item in self.segments],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingTranslation":
        if not isinstance(data, Mapping):
            raise DubbingError("dubbing translation must be an object")
        allowed = {
            "schema_version",
            "translation_id",
            "dubbing_id",
            "transcript_sha256",
            "target_language",
            "segments",
        }
        _strict_fields(data, allowed=allowed, kind="dubbing translation")
        if not isinstance(data["segments"], list):
            raise DubbingError("segments must be a list")
        return cls(
            schema_version=data["schema_version"],
            translation_id=data["translation_id"],
            dubbing_id=data["dubbing_id"],
            transcript_sha256=data["transcript_sha256"],
            target_language=data["target_language"],
            segments=tuple(TranslationSegment.from_dict(item) for item in data["segments"]),
        )


@dataclass(frozen=True)
class DubbingState:
    transcripts: tuple[DubbingTranscript, ...] = ()
    translations: tuple[DubbingTranslation, ...] = ()
    schema_version: int = DUBBING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DUBBING_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise DubbingError(f"unsupported dubbing state schema: {self.schema_version!r}")
        transcripts = tuple(self.transcripts)
        translations = tuple(self.translations)
        if not all(isinstance(item, DubbingTranscript) for item in transcripts):
            raise DubbingError("transcripts must contain DubbingTranscript values")
        if not all(isinstance(item, DubbingTranslation) for item in translations):
            raise DubbingError("translations must contain DubbingTranslation values")
        dubbing_ids = [item.dubbing_id for item in transcripts]
        if len(dubbing_ids) != len(set(dubbing_ids)):
            raise DubbingError("only one transcript may exist per dubbing_id")
        translation_ids = [item.translation_id for item in translations]
        if len(translation_ids) != len(set(translation_ids)):
            raise DubbingError("translation_id values must be unique")
        object.__setattr__(self, "transcripts", tuple(sorted(transcripts, key=lambda item: item.dubbing_id)))
        object.__setattr__(
            self,
            "translations",
            tuple(sorted(translations, key=lambda item: item.translation_id)),
        )
        self._validate_relationships()

    def _validate_relationships(self) -> None:
        by_dubbing = {item.dubbing_id: item for item in self.transcripts}
        for translation in self.translations:
            transcript = by_dubbing.get(translation.dubbing_id)
            if transcript is None:
                raise DubbingError(
                    f"translation {translation.translation_id!r} references missing dubbing transcript"
                )
            if translation.transcript_sha256 != transcript.digest:
                raise DubbingError(
                    f"translation {translation.translation_id!r} is stale because its transcript changed"
                )
            expected_ids = {item.segment_id for item in transcript.segments}
            actual_ids = {item.segment_id for item in translation.segments}
            if actual_ids != expected_ids:
                raise DubbingError(
                    f"translation {translation.translation_id!r} must translate every transcript segment exactly once"
                )
            if translation.target_language == transcript.language:
                raise DubbingError("translation target_language must differ from transcript language")

    def get_transcript(self, dubbing_id: str) -> DubbingTranscript:
        normalized = _identifier(dubbing_id, field_name="dubbing_id")
        for item in self.transcripts:
            if item.dubbing_id == normalized:
                return item
        raise DubbingTranscriptNotFound(normalized)

    def get_translation(self, translation_id: str) -> DubbingTranslation:
        normalized = _identifier(translation_id, field_name="translation_id")
        for item in self.translations:
            if item.translation_id == normalized:
                return item
        raise DubbingTranslationNotFound(normalized)

    def upsert_transcript(self, transcript: DubbingTranscript) -> "DubbingState":
        existing_translations = [
            item for item in self.translations if item.dubbing_id == transcript.dubbing_id
        ]
        if existing_translations:
            previous = next(
                (item for item in self.transcripts if item.dubbing_id == transcript.dubbing_id),
                None,
            )
            if previous is None or previous.digest != transcript.digest:
                raise DubbingError(
                    "cannot change a transcript while translations are bound to its current revision"
                )
        return DubbingState(
            transcripts=tuple(
                item for item in self.transcripts if item.dubbing_id != transcript.dubbing_id
            )
            + (transcript,),
            translations=self.translations,
        )

    def upsert_translation(self, translation: DubbingTranslation) -> "DubbingState":
        return DubbingState(
            transcripts=self.transcripts,
            translations=tuple(
                item
                for item in self.translations
                if item.translation_id != translation.translation_id
            )
            + (translation,),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "transcripts": [item.to_dict() for item in self.transcripts],
            "translations": [item.to_dict() for item in self.translations],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingState":
        if not isinstance(data, Mapping):
            raise DubbingError("dubbing state must be an object")
        allowed = {"schema_version", "transcripts", "translations"}
        _strict_fields(data, allowed=allowed, kind="dubbing state")
        if not isinstance(data["transcripts"], list) or not isinstance(data["translations"], list):
            raise DubbingError("transcripts and translations must be lists")
        return cls(
            schema_version=data["schema_version"],
            transcripts=tuple(DubbingTranscript.from_dict(item) for item in data["transcripts"]),
            translations=tuple(DubbingTranslation.from_dict(item) for item in data["translations"]),
        )


class DubbingStore:
    """Atomic canonical dubbing persistence bound to registered source media."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.source_media = ProjectSourceMediaStore(project_store)

    def _state_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                DUBBING_STATE_PATH,
                must_exist=False,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise DubbingError(str(exc)) from exc

    def load(self, project_id: str, *, validate_current: bool = False) -> DubbingState:
        self.project_store.load_project(project_id)
        path = self._state_path(project_id)
        if not path.exists():
            return DubbingState()
        if not path.is_file() or path.is_symlink():
            raise DubbingError("dubbing state path must be a regular project file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DubbingError("dubbing state is malformed JSON") from exc
        except OSError as exc:
            raise DubbingError("dubbing state could not be read") from exc
        state = DubbingState.from_dict(data)
        if validate_current:
            self._validate_sources(project_id, state)
        return state

    def _write(self, project_id: str, state: DubbingState) -> DubbingState:
        self.project_store._atomic_write_json(self._state_path(project_id), state.to_dict())
        return state

    def _validate_transcript_source(self, project_id: str, transcript: DubbingTranscript) -> None:
        try:
            source = self.source_media.get(project_id, transcript.source_id)
        except (SourceMediaNotFound, SourceMediaError, ProjectStoreError) as exc:
            raise DubbingError(
                f"dubbing transcript requires current registered source media: {exc}"
            ) from exc
        source_sha256 = source.metadata.get("sha256")
        if source_sha256 != transcript.source_sha256:
            raise DubbingError(
                f"dubbing transcript {transcript.dubbing_id!r} no longer matches source content"
            )
        duration_us = source.metadata.get("duration_us")
        if isinstance(duration_us, bool) or not isinstance(duration_us, int) or duration_us <= 0:
            raise DubbingError("registered source media is missing a valid duration_us")
        if transcript.end_us > duration_us:
            raise DubbingError("dubbing transcript range exceeds registered source duration")

    def _validate_sources(self, project_id: str, state: DubbingState) -> None:
        for transcript in state.transcripts:
            self._validate_transcript_source(project_id, transcript)

    def upsert_transcript(self, project_id: str, transcript: DubbingTranscript) -> DubbingState:
        if not isinstance(transcript, DubbingTranscript):
            raise DubbingError("upsert_transcript requires DubbingTranscript")
        with self.project_store._lock:
            current = self.load(project_id)
            self._validate_transcript_source(project_id, transcript)
            return self._write(project_id, current.upsert_transcript(transcript))

    def upsert_translation(self, project_id: str, translation: DubbingTranslation) -> DubbingState:
        if not isinstance(translation, DubbingTranslation):
            raise DubbingError("upsert_translation requires DubbingTranslation")
        with self.project_store._lock:
            current = self.load(project_id, validate_current=True)
            return self._write(project_id, current.upsert_translation(translation))

    def validate_project(self, project_id: str) -> DubbingState:
        return self.load(project_id, validate_current=True)
