"""Provider-neutral forced-alignment state bound to exact prepared speech revisions."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .dubbing import DubbingError, DubbingStore, DubbingTranslationNotFound
from .models import ProjectValidationError, validate_identifier
from .prepared_speech import (
    PreparedSpeechError,
    PreparedSpeechStore,
    PreparedSpeechTake,
    canonical_revision_sha256,
)
from .store import ProjectStore, ProjectStoreError

DUBBING_ALIGNMENT_SCHEMA_VERSION = 1
DUBBING_ALIGNMENT_PATH = "timeline/dubbing-alignments.json"
_ALIGNMENT_UNITS = frozenset({"word", "token", "phoneme"})
_MAX_ALIGNMENT_MARKS = 100_000
_MAX_MARK_TEXT_LENGTH = 512


class DubbingAlignmentError(ProjectValidationError):
    """Invalid or stale forced-alignment state."""


class DubbingAlignmentNotFound(DubbingAlignmentError):
    pass


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise DubbingAlignmentError(str(exc)) from exc


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise DubbingAlignmentError(f"{field_name} must be a lowercase SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise DubbingAlignmentError(f"{field_name} must be a lowercase SHA-256 hex digest") from exc
    return value


def _us(value: Any, *, field_name: str, positive: bool = False) -> int:
    minimum = 1 if positive else 0
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        qualifier = "positive" if positive else "non-negative"
        raise DubbingAlignmentError(f"{field_name} must be a {qualifier} integer microsecond value")
    return value


def _confidence(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DubbingAlignmentError("alignment confidence must be null or a finite number")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0 or parsed > 1.0:
        raise DubbingAlignmentError("alignment confidence must be between 0 and 1")
    return parsed


def _text(value: Any) -> str:
    if not isinstance(value, str):
        raise DubbingAlignmentError("alignment mark text must be a string")
    normalized = value.strip()
    if not normalized:
        raise DubbingAlignmentError("alignment mark text must not be empty")
    if len(normalized) > _MAX_MARK_TEXT_LENGTH:
        raise DubbingAlignmentError(
            f"alignment mark text must be <= {_MAX_MARK_TEXT_LENGTH} characters"
        )
    return normalized


@dataclass(frozen=True)
class DubbingAlignmentMark:
    mark_id: str
    unit: str
    text: str
    audio_start_us: int
    audio_end_us: int
    confidence: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "mark_id", _identifier(self.mark_id, field_name="mark_id"))
        if self.unit not in _ALIGNMENT_UNITS:
            raise DubbingAlignmentError(
                f"alignment unit must be one of {sorted(_ALIGNMENT_UNITS)!r}"
            )
        object.__setattr__(self, "text", _text(self.text))
        start = _us(self.audio_start_us, field_name="audio_start_us")
        end = _us(self.audio_end_us, field_name="audio_end_us", positive=True)
        if end <= start:
            raise DubbingAlignmentError("audio_end_us must be greater than audio_start_us")
        object.__setattr__(self, "audio_start_us", start)
        object.__setattr__(self, "audio_end_us", end)
        object.__setattr__(self, "confidence", _confidence(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "mark_id": self.mark_id,
            "unit": self.unit,
            "text": self.text,
            "audio_start_us": self.audio_start_us,
            "audio_end_us": self.audio_end_us,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingAlignmentMark":
        if not isinstance(data, Mapping):
            raise DubbingAlignmentError("alignment mark must be an object")
        allowed = {"mark_id", "unit", "text", "audio_start_us", "audio_end_us", "confidence"}
        unknown = set(data).difference(allowed)
        missing = allowed.difference(data)
        if unknown:
            raise DubbingAlignmentError(f"unsupported alignment mark fields: {sorted(unknown)!r}")
        if missing:
            raise DubbingAlignmentError(f"alignment mark is missing fields: {sorted(missing)!r}")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class DubbingAlignment:
    alignment_id: str
    take_id: str
    take_sha256: str
    dubbing_id: str
    script_kind: str
    script_id: str
    script_sha256: str
    audio_id: str
    audio_sha256: str
    language: str
    segment_id: str | None
    target_start_us: int
    target_end_us: int
    marks: tuple[DubbingAlignmentMark, ...]
    schema_version: int = DUBBING_ALIGNMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DUBBING_ALIGNMENT_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise DubbingAlignmentError(
                f"unsupported dubbing alignment schema: {self.schema_version!r}"
            )
        for field_name in ("alignment_id", "take_id", "dubbing_id", "script_id", "audio_id"):
            object.__setattr__(
                self,
                field_name,
                _identifier(getattr(self, field_name), field_name=field_name),
            )
        for field_name in ("take_sha256", "script_sha256", "audio_sha256"):
            object.__setattr__(
                self,
                field_name,
                _sha256(getattr(self, field_name), field_name=field_name),
            )
        if self.script_kind not in {"transcript", "translation"}:
            raise DubbingAlignmentError("script_kind must be transcript or translation")
        if not isinstance(self.language, str) or not self.language.strip():
            raise DubbingAlignmentError("alignment language must be a non-empty string")
        object.__setattr__(self, "language", self.language.strip().lower())
        if self.segment_id is not None:
            object.__setattr__(
                self,
                "segment_id",
                _identifier(self.segment_id, field_name="segment_id"),
            )
        start = _us(self.target_start_us, field_name="target_start_us")
        end = _us(self.target_end_us, field_name="target_end_us", positive=True)
        if end <= start:
            raise DubbingAlignmentError("target_end_us must be greater than target_start_us")
        object.__setattr__(self, "target_start_us", start)
        object.__setattr__(self, "target_end_us", end)
        marks = tuple(self.marks)
        if not marks or not all(isinstance(item, DubbingAlignmentMark) for item in marks):
            raise DubbingAlignmentError("forced alignment requires at least one typed mark")
        if len(marks) > _MAX_ALIGNMENT_MARKS:
            raise DubbingAlignmentError(
                f"forced alignment supports at most {_MAX_ALIGNMENT_MARKS} marks"
            )
        ids = [item.mark_id for item in marks]
        if len(ids) != len(set(ids)):
            raise DubbingAlignmentError("alignment mark_id values must be unique")
        ordered = tuple(sorted(marks, key=lambda item: (item.audio_start_us, item.audio_end_us, item.mark_id)))
        previous: DubbingAlignmentMark | None = None
        for mark in ordered:
            if previous is not None and mark.audio_start_us < previous.audio_end_us:
                raise DubbingAlignmentError(
                    f"alignment marks must not overlap: {previous.mark_id!r} and {mark.mark_id!r}"
                )
            previous = mark
        object.__setattr__(self, "marks", ordered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "alignment_id": self.alignment_id,
            "take_id": self.take_id,
            "take_sha256": self.take_sha256,
            "dubbing_id": self.dubbing_id,
            "script_kind": self.script_kind,
            "script_id": self.script_id,
            "script_sha256": self.script_sha256,
            "audio_id": self.audio_id,
            "audio_sha256": self.audio_sha256,
            "language": self.language,
            "segment_id": self.segment_id,
            "target_start_us": self.target_start_us,
            "target_end_us": self.target_end_us,
            "marks": [item.to_dict() for item in self.marks],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingAlignment":
        if not isinstance(data, Mapping):
            raise DubbingAlignmentError("dubbing alignment must be an object")
        allowed = {
            "schema_version",
            "alignment_id",
            "take_id",
            "take_sha256",
            "dubbing_id",
            "script_kind",
            "script_id",
            "script_sha256",
            "audio_id",
            "audio_sha256",
            "language",
            "segment_id",
            "target_start_us",
            "target_end_us",
            "marks",
        }
        unknown = set(data).difference(allowed)
        missing = allowed.difference(data)
        if unknown:
            raise DubbingAlignmentError(f"unsupported dubbing alignment fields: {sorted(unknown)!r}")
        if missing:
            raise DubbingAlignmentError(f"dubbing alignment is missing fields: {sorted(missing)!r}")
        if not isinstance(data["marks"], list):
            raise DubbingAlignmentError("dubbing alignment marks must be a list")
        return cls(
            **{key: data[key] for key in allowed if key != "marks"},
            marks=tuple(DubbingAlignmentMark.from_dict(item) for item in data["marks"]),
        )


@dataclass(frozen=True)
class DubbingAlignmentState:
    alignments: tuple[DubbingAlignment, ...] = ()
    schema_version: int = DUBBING_ALIGNMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DUBBING_ALIGNMENT_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise DubbingAlignmentError(
                f"unsupported dubbing alignment state schema: {self.schema_version!r}"
            )
        alignments = tuple(self.alignments)
        if not all(isinstance(item, DubbingAlignment) for item in alignments):
            raise DubbingAlignmentError("alignments must contain DubbingAlignment values")
        ids = [item.alignment_id for item in alignments]
        if len(ids) != len(set(ids)):
            raise DubbingAlignmentError("alignment_id values must be unique")
        take_ids = [item.take_id for item in alignments]
        if len(take_ids) != len(set(take_ids)):
            raise DubbingAlignmentError("only one current alignment may exist per prepared speech take")
        object.__setattr__(
            self,
            "alignments",
            tuple(sorted(alignments, key=lambda item: item.alignment_id)),
        )

    def get(self, alignment_id: str) -> DubbingAlignment:
        normalized = _identifier(alignment_id, field_name="alignment_id")
        for item in self.alignments:
            if item.alignment_id == normalized:
                return item
        raise DubbingAlignmentNotFound(normalized)

    def for_take(self, take_id: str) -> DubbingAlignment | None:
        normalized = _identifier(take_id, field_name="take_id")
        return next((item for item in self.alignments if item.take_id == normalized), None)

    def upsert(self, alignment: DubbingAlignment) -> "DubbingAlignmentState":
        return DubbingAlignmentState(
            alignments=tuple(item for item in self.alignments if item.take_id != alignment.take_id)
            + (alignment,)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "alignments": [item.to_dict() for item in self.alignments],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DubbingAlignmentState":
        if not isinstance(data, Mapping):
            raise DubbingAlignmentError("dubbing alignment state must be an object")
        allowed = {"schema_version", "alignments"}
        unknown = set(data).difference(allowed)
        missing = allowed.difference(data)
        if unknown:
            raise DubbingAlignmentError(f"unsupported dubbing alignment state fields: {sorted(unknown)!r}")
        if missing:
            raise DubbingAlignmentError(f"dubbing alignment state is missing fields: {sorted(missing)!r}")
        if not isinstance(data["alignments"], list):
            raise DubbingAlignmentError("dubbing alignment state alignments must be a list")
        return cls(
            schema_version=data["schema_version"],
            alignments=tuple(DubbingAlignment.from_dict(item) for item in data["alignments"]),
        )


class DubbingAlignmentStore:
    """Persist forced alignment while revalidating exact take/script/audio revisions."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.prepared_speech = PreparedSpeechStore(project_store)
        self.dubbing = DubbingStore(project_store)

    def _path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                DUBBING_ALIGNMENT_PATH,
                must_exist=False,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise DubbingAlignmentError(str(exc)) from exc

    def load(self, project_id: str, *, validate_current: bool = False) -> DubbingAlignmentState:
        self.project_store.load_project(project_id)
        path = self._path(project_id)
        if not path.exists():
            return DubbingAlignmentState()
        if not path.is_file() or path.is_symlink():
            raise DubbingAlignmentError("dubbing alignment state must be a regular project file")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DubbingAlignmentError("dubbing alignment state is malformed JSON") from exc
        except OSError as exc:
            raise DubbingAlignmentError("dubbing alignment state could not be read") from exc
        state = DubbingAlignmentState.from_dict(payload)
        if validate_current:
            self._validate_state(project_id, state)
        return state

    def _write(self, project_id: str, state: DubbingAlignmentState) -> DubbingAlignmentState:
        self.project_store._atomic_write_json(self._path(project_id), state.to_dict())
        return state

    def _target_and_language(self, project_id: str, take: PreparedSpeechTake) -> tuple[int, int, str]:
        try:
            dubbing = self.dubbing.validate_project(project_id)
            transcript = dubbing.get_transcript(take.dubbing_id)
        except DubbingError as exc:
            raise DubbingAlignmentError(
                f"alignment take {take.take_id!r} references unavailable transcript"
            ) from exc
        if take.segment_id is None:
            start_us, end_us = transcript.start_us, transcript.end_us
        else:
            segment = next(
                (item for item in transcript.segments if item.segment_id == take.segment_id),
                None,
            )
            if segment is None:
                raise DubbingAlignmentError(
                    f"alignment take {take.take_id!r} references unavailable segment"
                )
            start_us, end_us = segment.start_us, segment.end_us
        language = transcript.language
        if take.script_kind == "translation":
            try:
                translation = dubbing.get_translation(take.script_id)
            except DubbingTranslationNotFound as exc:
                raise DubbingAlignmentError(
                    f"alignment take {take.take_id!r} references unavailable translation"
                ) from exc
            language = translation.target_language
        return start_us, end_us, language

    def _validate_alignment(self, project_id: str, alignment: DubbingAlignment) -> None:
        try:
            take = self.prepared_speech.validate_project(project_id).get(alignment.take_id)
        except PreparedSpeechError as exc:
            raise DubbingAlignmentError(
                f"alignment {alignment.alignment_id!r} references unavailable prepared speech"
            ) from exc
        if alignment.take_sha256 != canonical_revision_sha256(take.to_dict()):
            raise DubbingAlignmentError(
                f"alignment {alignment.alignment_id!r} is stale because its prepared speech take changed"
            )
        for field_name in (
            "dubbing_id",
            "script_kind",
            "script_id",
            "script_sha256",
            "audio_id",
            "audio_sha256",
            "segment_id",
        ):
            if getattr(alignment, field_name) != getattr(take, field_name):
                raise DubbingAlignmentError(
                    f"alignment {alignment.alignment_id!r} {field_name} does not match current prepared speech"
                )
        expected_start, expected_end, expected_language = self._target_and_language(project_id, take)
        if (alignment.target_start_us, alignment.target_end_us) != (expected_start, expected_end):
            raise DubbingAlignmentError(
                f"alignment {alignment.alignment_id!r} target range no longer matches current script"
            )
        if alignment.language != expected_language:
            raise DubbingAlignmentError(
                f"alignment {alignment.alignment_id!r} language no longer matches current script"
            )
        for mark in alignment.marks:
            if mark.audio_end_us > take.duration_us:
                raise DubbingAlignmentError(
                    f"alignment mark {mark.mark_id!r} exceeds prepared speech duration"
                )

    def _validate_state(self, project_id: str, state: DubbingAlignmentState) -> None:
        for alignment in state.alignments:
            self._validate_alignment(project_id, alignment)

    def upsert(self, project_id: str, alignment: DubbingAlignment) -> DubbingAlignmentState:
        if not isinstance(alignment, DubbingAlignment):
            raise DubbingAlignmentError("upsert requires DubbingAlignment")
        with self.project_store._lock:
            current = self.load(project_id, validate_current=True)
            self._validate_alignment(project_id, alignment)
            return self._write(project_id, current.upsert(alignment))

    def validate_project(self, project_id: str) -> DubbingAlignmentState:
        return self.load(project_id, validate_current=True)
