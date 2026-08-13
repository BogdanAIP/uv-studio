"""Typed prepared speech takes bound to exact dubbing script and audio revisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .dubbing import (
    DubbingError,
    DubbingStore,
    DubbingTranscriptNotFound,
    DubbingTranslationNotFound,
)
from .models import ProjectValidationError, validate_identifier
from .prepared_audio import (
    PreparedAudioError,
    PreparedAudioNotFound,
    ProjectPreparedAudioStore,
)
from .store import ProjectStore, ProjectStoreError

PREPARED_SPEECH_SCHEMA_VERSION = 1
PREPARED_SPEECH_STATE_PATH = "timeline/prepared-speech.json"
_SCRIPT_KINDS = frozenset({"transcript", "translation"})
_ORIGINS = frozenset({"imported", "recorded", "tts"})
_SHA256_HEX_LENGTH = 64


class PreparedSpeechError(ProjectValidationError):
    """Invalid or stale prepared speech state."""


class PreparedSpeechTakeNotFound(PreparedSpeechError):
    pass


def canonical_revision_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise PreparedSpeechError(str(exc)) from exc


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != _SHA256_HEX_LENGTH or value != value.lower():
        raise PreparedSpeechError(f"{field_name} must be a lowercase SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise PreparedSpeechError(f"{field_name} must be a lowercase SHA-256 hex digest") from exc
    return value


def _positive_duration(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PreparedSpeechError("duration_us must be a positive integer")
    return value


@dataclass(frozen=True)
class PreparedSpeechTake:
    take_id: str
    dubbing_id: str
    script_kind: str
    script_id: str
    script_sha256: str
    audio_id: str
    audio_sha256: str
    duration_us: int
    origin: str
    segment_id: str | None = None
    schema_version: int = PREPARED_SPEECH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PREPARED_SPEECH_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise PreparedSpeechError(
                f"unsupported prepared speech schema: {self.schema_version!r}"
            )
        object.__setattr__(self, "take_id", _identifier(self.take_id, field_name="take_id"))
        object.__setattr__(self, "dubbing_id", _identifier(self.dubbing_id, field_name="dubbing_id"))
        if self.script_kind not in _SCRIPT_KINDS:
            raise PreparedSpeechError(f"script_kind must be one of {sorted(_SCRIPT_KINDS)!r}")
        object.__setattr__(self, "script_id", _identifier(self.script_id, field_name="script_id"))
        object.__setattr__(
            self,
            "script_sha256",
            _sha256(self.script_sha256, field_name="script_sha256"),
        )
        object.__setattr__(self, "audio_id", _identifier(self.audio_id, field_name="audio_id"))
        object.__setattr__(
            self,
            "audio_sha256",
            _sha256(self.audio_sha256, field_name="audio_sha256"),
        )
        object.__setattr__(self, "duration_us", _positive_duration(self.duration_us))
        if self.origin not in _ORIGINS:
            raise PreparedSpeechError(f"origin must be one of {sorted(_ORIGINS)!r}")
        if self.segment_id is not None:
            object.__setattr__(
                self,
                "segment_id",
                _identifier(self.segment_id, field_name="segment_id"),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "take_id": self.take_id,
            "dubbing_id": self.dubbing_id,
            "script_kind": self.script_kind,
            "script_id": self.script_id,
            "script_sha256": self.script_sha256,
            "audio_id": self.audio_id,
            "audio_sha256": self.audio_sha256,
            "duration_us": self.duration_us,
            "origin": self.origin,
            "segment_id": self.segment_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PreparedSpeechTake":
        if not isinstance(data, Mapping):
            raise PreparedSpeechError("prepared speech take must be an object")
        allowed = {
            "schema_version",
            "take_id",
            "dubbing_id",
            "script_kind",
            "script_id",
            "script_sha256",
            "audio_id",
            "audio_sha256",
            "duration_us",
            "origin",
            "segment_id",
        }
        unknown = set(data).difference(allowed)
        missing = allowed.difference(data)
        if unknown:
            raise PreparedSpeechError(f"unsupported prepared speech fields: {sorted(unknown)!r}")
        if missing:
            raise PreparedSpeechError(f"prepared speech is missing fields: {sorted(missing)!r}")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class PreparedSpeechState:
    takes: tuple[PreparedSpeechTake, ...] = ()
    schema_version: int = PREPARED_SPEECH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PREPARED_SPEECH_SCHEMA_VERSION or isinstance(self.schema_version, bool):
            raise PreparedSpeechError(
                f"unsupported prepared speech state schema: {self.schema_version!r}"
            )
        takes = tuple(self.takes)
        if not all(isinstance(item, PreparedSpeechTake) for item in takes):
            raise PreparedSpeechError("takes must contain PreparedSpeechTake values")
        ids = [item.take_id for item in takes]
        if len(ids) != len(set(ids)):
            raise PreparedSpeechError("prepared speech take_id values must be unique")
        object.__setattr__(self, "takes", tuple(sorted(takes, key=lambda item: item.take_id)))

    def upsert(self, take: PreparedSpeechTake) -> "PreparedSpeechState":
        return PreparedSpeechState(
            takes=tuple(item for item in self.takes if item.take_id != take.take_id) + (take,)
        )

    def get(self, take_id: str) -> PreparedSpeechTake:
        normalized = _identifier(take_id, field_name="take_id")
        for item in self.takes:
            if item.take_id == normalized:
                return item
        raise PreparedSpeechTakeNotFound(normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "takes": [item.to_dict() for item in self.takes],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PreparedSpeechState":
        if not isinstance(data, Mapping):
            raise PreparedSpeechError("prepared speech state must be an object")
        allowed = {"schema_version", "takes"}
        unknown = set(data).difference(allowed)
        missing = allowed.difference(data)
        if unknown:
            raise PreparedSpeechError(f"unsupported prepared speech state fields: {sorted(unknown)!r}")
        if missing:
            raise PreparedSpeechError(f"prepared speech state is missing fields: {sorted(missing)!r}")
        if not isinstance(data["takes"], list):
            raise PreparedSpeechError("prepared speech takes must be a list")
        return cls(
            schema_version=data["schema_version"],
            takes=tuple(PreparedSpeechTake.from_dict(item) for item in data["takes"]),
        )


class PreparedSpeechStore:
    """Atomic speech-take state validated against current script and audio revisions."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.dubbing = DubbingStore(project_store)
        self.audio = ProjectPreparedAudioStore(project_store)

    def _state_path(self, project_id: str) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                PREPARED_SPEECH_STATE_PATH,
                must_exist=False,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise PreparedSpeechError(str(exc)) from exc

    def load(self, project_id: str, *, validate_current: bool = False) -> PreparedSpeechState:
        self.project_store.load_project(project_id)
        path = self._state_path(project_id)
        if not path.exists():
            return PreparedSpeechState()
        if not path.is_file() or path.is_symlink():
            raise PreparedSpeechError("prepared speech state must be a regular project file")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PreparedSpeechError("prepared speech state is malformed JSON") from exc
        except OSError as exc:
            raise PreparedSpeechError("prepared speech state could not be read") from exc
        state = PreparedSpeechState.from_dict(payload)
        if validate_current:
            self._validate_state(project_id, state)
        return state

    def _write(self, project_id: str, state: PreparedSpeechState) -> PreparedSpeechState:
        self.project_store._atomic_write_json(self._state_path(project_id), state.to_dict())
        return state

    def _validate_script(self, project_id: str, take: PreparedSpeechTake) -> None:
        try:
            dubbing = self.dubbing.validate_project(project_id)
            transcript = dubbing.get_transcript(take.dubbing_id)
        except (DubbingError, DubbingTranscriptNotFound) as exc:
            raise PreparedSpeechError(
                f"prepared speech take {take.take_id!r} references unavailable transcript"
            ) from exc

        transcript_segment_ids = {item.segment_id for item in transcript.segments}
        if take.segment_id is not None and take.segment_id not in transcript_segment_ids:
            raise PreparedSpeechError(
                f"prepared speech take {take.take_id!r} references missing transcript segment"
            )

        if take.script_kind == "transcript":
            if take.script_id != transcript.dubbing_id:
                raise PreparedSpeechError("transcript speech take script_id must equal dubbing_id")
            expected_sha256 = transcript.digest
        else:
            try:
                translation = dubbing.get_translation(take.script_id)
            except DubbingTranslationNotFound as exc:
                raise PreparedSpeechError(
                    f"prepared speech take {take.take_id!r} references missing translation"
                ) from exc
            if translation.dubbing_id != transcript.dubbing_id:
                raise PreparedSpeechError("translation speech take belongs to a different dubbing transcript")
            translation_segment_ids = {item.segment_id for item in translation.segments}
            if take.segment_id is not None and take.segment_id not in translation_segment_ids:
                raise PreparedSpeechError(
                    f"prepared speech take {take.take_id!r} references missing translation segment"
                )
            expected_sha256 = canonical_revision_sha256(translation.to_dict())

        if take.script_sha256 != expected_sha256:
            raise PreparedSpeechError(
                f"prepared speech take {take.take_id!r} is stale because its script changed"
            )

    def _validate_audio(self, project_id: str, take: PreparedSpeechTake) -> None:
        try:
            audio = self.audio.validate_reference(project_id, take.audio_id)
        except (PreparedAudioNotFound, PreparedAudioError) as exc:
            raise PreparedSpeechError(
                f"prepared speech take {take.take_id!r} references unavailable audio"
            ) from exc
        if audio.metadata.get("sha256") != take.audio_sha256:
            raise PreparedSpeechError(
                f"prepared speech take {take.take_id!r} is stale because its audio changed"
            )
        if audio.metadata.get("duration_us") != take.duration_us:
            raise PreparedSpeechError(
                f"prepared speech take {take.take_id!r} duration no longer matches its audio"
            )
        if audio.metadata.get("origin") != take.origin:
            raise PreparedSpeechError(
                f"prepared speech take {take.take_id!r} origin does not match registered audio"
            )

    def _validate_take(self, project_id: str, take: PreparedSpeechTake) -> None:
        self._validate_script(project_id, take)
        self._validate_audio(project_id, take)

    def _validate_state(self, project_id: str, state: PreparedSpeechState) -> None:
        for take in state.takes:
            self._validate_take(project_id, take)

    def upsert(self, project_id: str, take: PreparedSpeechTake) -> PreparedSpeechState:
        if not isinstance(take, PreparedSpeechTake):
            raise PreparedSpeechError("upsert requires PreparedSpeechTake")
        with self.project_store._lock:
            current = self.load(project_id, validate_current=True)
            self._validate_take(project_id, take)
            return self._write(project_id, current.upsert(take))

    def validate_project(self, project_id: str) -> PreparedSpeechState:
        return self.load(project_id, validate_current=True)

    def has_dubbing_bindings(self, project_id: str, dubbing_id: str) -> bool:
        state = self.load(project_id)
        return any(item.dubbing_id == dubbing_id for item in state.takes)

    def has_translation_bindings(self, project_id: str, translation_id: str) -> bool:
        state = self.load(project_id)
        return any(
            item.script_kind == "translation" and item.script_id == translation_id
            for item in state.takes
        )
