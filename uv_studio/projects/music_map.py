"""Provider-neutral music timing map for optional Stage 7 music-video projects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from .media_integrity import MediaIntegrityError, verify_registered_media_bytes
from .models import (
    ProjectReference,
    ProjectValidationError,
    validate_identifier,
    validate_project_relative_path,
)
from .store import ProjectStore, ProjectStoreError

MUSIC_MAP_SCHEMA_VERSION = 1
MUSIC_MAP_PATH = "timeline/music-map.json"
MAX_MUSIC_SECTIONS = 256
MAX_MUSIC_MARKERS = 4096
MAX_LYRIC_PHRASES = 1024
_SECTION_KINDS = frozenset(
    {
        "intro",
        "verse",
        "pre_chorus",
        "chorus",
        "bridge",
        "drop",
        "breakdown",
        "outro",
        "instrumental",
        "other",
    }
)
_MARKER_KINDS = frozenset(
    {"beat", "downbeat", "accent", "climax", "phrase_boundary", "cut_point"}
)
_MEDIA_ROOTS = frozenset({"sources", "assets", "artifacts", "exports"})


class MusicMapError(ProjectValidationError):
    """Invalid, stale, or unsafe music-map state."""


def _strict_fields(data: Mapping[str, Any], *, allowed: set[str], kind: str) -> None:
    unknown = set(data).difference(allowed)
    missing = allowed.difference(data)
    if unknown:
        raise MusicMapError(f"unsupported {kind} fields: {sorted(unknown)!r}")
    if missing:
        raise MusicMapError(f"{kind} is missing fields: {sorted(missing)!r}")


def _identifier(value: Any, *, field_name: str) -> str:
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise MusicMapError(str(exc)) from exc


def _text(value: Any, *, field_name: str, maximum: int = 4000) -> str:
    if not isinstance(value, str):
        raise MusicMapError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise MusicMapError(f"{field_name} must not be empty")
    if len(normalized) > maximum:
        raise MusicMapError(f"{field_name} must be <= {maximum} characters")
    return normalized


def _sha256(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise MusicMapError(f"{field_name} must be a 64-character sha256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MusicMapError(f"{field_name} must be hexadecimal sha256") from exc
    return value.lower()


def _positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MusicMapError(f"{field_name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MusicMapError(f"{field_name} must be a non-negative integer")
    return value


def _canonical_sha(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True)
class MusicSourceBinding:
    reference_id: str
    reference_path: str
    sha256: str
    size_bytes: int
    duration_us: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reference_id", _identifier(self.reference_id, field_name="song reference_id")
        )
        try:
            path = validate_project_relative_path(self.reference_path)
        except ProjectValidationError as exc:
            raise MusicMapError(str(exc)) from exc
        object.__setattr__(self, "reference_path", path)
        object.__setattr__(self, "sha256", _sha256(self.sha256, field_name="song sha256"))
        object.__setattr__(
            self, "size_bytes", _positive_int(self.size_bytes, field_name="song size_bytes")
        )
        object.__setattr__(
            self, "duration_us", _positive_int(self.duration_us, field_name="song duration_us")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "reference_path": self.reference_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "duration_us": self.duration_us,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicSourceBinding":
        if not isinstance(data, Mapping):
            raise MusicMapError("song binding must be an object")
        allowed = {"reference_id", "reference_path", "sha256", "size_bytes", "duration_us"}
        _strict_fields(data, allowed=allowed, kind="song binding")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class MusicExcerpt:
    start_us: int
    end_us: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "start_us", _nonnegative_int(self.start_us, field_name="excerpt start_us")
        )
        object.__setattr__(
            self, "end_us", _positive_int(self.end_us, field_name="excerpt end_us")
        )
        if self.end_us <= self.start_us:
            raise MusicMapError("excerpt end_us must be greater than start_us")

    @property
    def duration_us(self) -> int:
        return self.end_us - self.start_us

    def to_dict(self) -> dict[str, int]:
        return {"start_us": self.start_us, "end_us": self.end_us}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicExcerpt":
        if not isinstance(data, Mapping):
            raise MusicMapError("music excerpt must be an object")
        allowed = {"start_us", "end_us"}
        _strict_fields(data, allowed=allowed, kind="music excerpt")
        return cls(start_us=data["start_us"], end_us=data["end_us"])


@dataclass(frozen=True)
class MusicSection:
    section_id: str
    kind: str
    label: str
    start_us: int
    end_us: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "section_id", _identifier(self.section_id, field_name="music section_id")
        )
        if not isinstance(self.kind, str) or self.kind not in _SECTION_KINDS:
            raise MusicMapError(f"music section kind must be one of {sorted(_SECTION_KINDS)!r}")
        object.__setattr__(
            self, "label", _text(self.label, field_name="music section label", maximum=512)
        )
        object.__setattr__(
            self, "start_us", _nonnegative_int(self.start_us, field_name="music section start_us")
        )
        object.__setattr__(
            self, "end_us", _positive_int(self.end_us, field_name="music section end_us")
        )
        if self.end_us <= self.start_us:
            raise MusicMapError("music section end_us must be greater than start_us")

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "kind": self.kind,
            "label": self.label,
            "start_us": self.start_us,
            "end_us": self.end_us,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicSection":
        if not isinstance(data, Mapping):
            raise MusicMapError("music section must be an object")
        allowed = {"section_id", "kind", "label", "start_us", "end_us"}
        _strict_fields(data, allowed=allowed, kind="music section")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class MusicTimingMarker:
    marker_id: str
    kind: str
    time_us: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "marker_id", _identifier(self.marker_id, field_name="music marker_id")
        )
        if not isinstance(self.kind, str) or self.kind not in _MARKER_KINDS:
            raise MusicMapError(f"music marker kind must be one of {sorted(_MARKER_KINDS)!r}")
        object.__setattr__(
            self, "time_us", _nonnegative_int(self.time_us, field_name="music marker time_us")
        )

    def to_dict(self) -> dict[str, Any]:
        return {"marker_id": self.marker_id, "kind": self.kind, "time_us": self.time_us}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicTimingMarker":
        if not isinstance(data, Mapping):
            raise MusicMapError("music timing marker must be an object")
        allowed = {"marker_id", "kind", "time_us"}
        _strict_fields(data, allowed=allowed, kind="music timing marker")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class MusicLyricPhrase:
    phrase_id: str
    start_us: int
    end_us: int
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "phrase_id", _identifier(self.phrase_id, field_name="lyric phrase_id")
        )
        object.__setattr__(
            self, "start_us", _nonnegative_int(self.start_us, field_name="lyric phrase start_us")
        )
        object.__setattr__(
            self, "end_us", _positive_int(self.end_us, field_name="lyric phrase end_us")
        )
        if self.end_us <= self.start_us:
            raise MusicMapError("lyric phrase end_us must be greater than start_us")
        object.__setattr__(self, "text", _text(self.text, field_name="lyric phrase text"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "phrase_id": self.phrase_id,
            "start_us": self.start_us,
            "end_us": self.end_us,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicLyricPhrase":
        if not isinstance(data, Mapping):
            raise MusicMapError("lyric phrase must be an object")
        allowed = {"phrase_id", "start_us", "end_us", "text"}
        _strict_fields(data, allowed=allowed, kind="lyric phrase")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class MusicMapState:
    song: MusicSourceBinding
    excerpt: MusicExcerpt
    sections: tuple[MusicSection, ...] = ()
    markers: tuple[MusicTimingMarker, ...] = ()
    lyric_phrases: tuple[MusicLyricPhrase, ...] = ()
    schema_version: int = MUSIC_MAP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != MUSIC_MAP_SCHEMA_VERSION
        ):
            raise MusicMapError(f"unsupported music-map schema: {self.schema_version!r}")
        if not isinstance(self.song, MusicSourceBinding):
            raise MusicMapError("song must be a MusicSourceBinding")
        if not isinstance(self.excerpt, MusicExcerpt):
            raise MusicMapError("excerpt must be a MusicExcerpt")
        if self.excerpt.end_us > self.song.duration_us:
            raise MusicMapError("music excerpt exceeds current song duration")

        sections = tuple(
            sorted(self.sections, key=lambda item: (item.start_us, item.end_us, item.section_id))
        )
        markers = tuple(sorted(self.markers, key=lambda item: (item.time_us, item.marker_id)))
        phrases = tuple(
            sorted(
                self.lyric_phrases,
                key=lambda item: (item.start_us, item.end_us, item.phrase_id),
            )
        )
        if len(sections) > MAX_MUSIC_SECTIONS:
            raise MusicMapError(f"music sections must contain at most {MAX_MUSIC_SECTIONS} items")
        if len(markers) > MAX_MUSIC_MARKERS:
            raise MusicMapError(f"music markers must contain at most {MAX_MUSIC_MARKERS} items")
        if len(phrases) > MAX_LYRIC_PHRASES:
            raise MusicMapError(f"lyric phrases must contain at most {MAX_LYRIC_PHRASES} items")
        if not all(isinstance(item, MusicSection) for item in sections):
            raise MusicMapError("music sections contain invalid values")
        if not all(isinstance(item, MusicTimingMarker) for item in markers):
            raise MusicMapError("music markers contain invalid values")
        if not all(isinstance(item, MusicLyricPhrase) for item in phrases):
            raise MusicMapError("lyric phrases contain invalid values")
        for values, label in (
            ([item.section_id for item in sections], "music section IDs"),
            ([item.marker_id for item in markers], "music marker IDs"),
            ([item.phrase_id for item in phrases], "lyric phrase IDs"),
        ):
            if len(values) != len(set(values)):
                raise MusicMapError(f"{label} must be unique")

        previous_end: int | None = None
        for section in sections:
            self._require_inside_excerpt(section.start_us, section.end_us, "music section")
            if previous_end is not None and section.start_us < previous_end:
                raise MusicMapError("music sections must not overlap")
            previous_end = section.end_us
        for marker in markers:
            if marker.time_us < self.excerpt.start_us or marker.time_us >= self.excerpt.end_us:
                raise MusicMapError("music marker must fall inside the half-open excerpt")
        for phrase in phrases:
            self._require_inside_excerpt(phrase.start_us, phrase.end_us, "lyric phrase")

        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "markers", markers)
        object.__setattr__(self, "lyric_phrases", phrases)

    def _require_inside_excerpt(self, start_us: int, end_us: int, kind: str) -> None:
        if start_us < self.excerpt.start_us or end_us > self.excerpt.end_us:
            raise MusicMapError(f"{kind} must stay inside the selected excerpt")

    def identity_dict(self) -> dict[str, Any]:
        return {
            "song": self.song.to_dict(),
            "excerpt": self.excerpt.to_dict(),
            "sections": [item.to_dict() for item in self.sections],
            "markers": [item.to_dict() for item in self.markers],
            "lyric_phrases": [item.to_dict() for item in self.lyric_phrases],
        }

    @property
    def revision_sha256(self) -> str:
        return _canonical_sha(self.identity_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            **self.identity_dict(),
            "revision_sha256": self.revision_sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicMapState":
        if not isinstance(data, Mapping):
            raise MusicMapError("music map must be an object")
        allowed = {
            "schema_version",
            "song",
            "excerpt",
            "sections",
            "markers",
            "lyric_phrases",
            "revision_sha256",
        }
        _strict_fields(data, allowed=allowed, kind="music map")
        for field_name in ("sections", "markers", "lyric_phrases"):
            if not isinstance(data[field_name], list):
                raise MusicMapError(f"{field_name} must be a list")
        value = cls(
            schema_version=data["schema_version"],
            song=MusicSourceBinding.from_dict(data["song"]),
            excerpt=MusicExcerpt.from_dict(data["excerpt"]),
            sections=tuple(MusicSection.from_dict(item) for item in data["sections"]),
            markers=tuple(MusicTimingMarker.from_dict(item) for item in data["markers"]),
            lyric_phrases=tuple(
                MusicLyricPhrase.from_dict(item) for item in data["lyric_phrases"]
            ),
        )
        if _sha256(data["revision_sha256"], field_name="revision_sha256") != value.revision_sha256:
            raise MusicMapError("stored music-map revision does not match map contents")
        return value


class MusicMapStore:
    """Atomic Project Store facade for optional music-specific timing state."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _path(self, project_id: str):
        return self.project_store.resolve_project_file(
            project_id, MUSIC_MAP_PATH, allowed_roots=("timeline",)
        )

    def load(self, project_id: str, *, validate_current: bool = False) -> MusicMapState | None:
        path = self._path(project_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            state = MusicMapState.from_dict(raw)
        except MusicMapError:
            raise
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise MusicMapError(f"invalid music-map state: {path}: {exc}") from exc
        if validate_current:
            self.validate_current(project_id, state)
        return state

    def set_map(
        self,
        project_id: str,
        *,
        song_reference_id: str,
        excerpt: MusicExcerpt,
        sections: tuple[MusicSection, ...] = (),
        markers: tuple[MusicTimingMarker, ...] = (),
        lyric_phrases: tuple[MusicLyricPhrase, ...] = (),
    ) -> MusicMapState:
        with self.project_store._lock:
            reference, path = self._resolve_song(project_id, song_reference_id)
            try:
                identity = verify_registered_media_bytes(path, reference.metadata)
            except MediaIntegrityError as exc:
                raise MusicMapError(str(exc)) from exc
            state = MusicMapState(
                song=MusicSourceBinding(
                    reference_id=reference.id,
                    reference_path=reference.path,
                    sha256=identity.sha256,
                    size_bytes=identity.size_bytes,
                    duration_us=self._duration_us(reference),
                ),
                excerpt=excerpt,
                sections=sections,
                markers=markers,
                lyric_phrases=lyric_phrases,
            )
            self._save(project_id, state)
            return state

    def clear(self, project_id: str) -> None:
        with self.project_store._lock:
            path = self._path(project_id)
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise ProjectStoreError("could not remove music-map state") from exc

    def validate_current(self, project_id: str, state: MusicMapState | None = None) -> None:
        state = state if state is not None else self.load(project_id)
        if state is None:
            return
        reference, path = self._resolve_song(project_id, state.song.reference_id)
        if reference.path != state.song.reference_path:
            raise MusicMapError("music-map song reference path changed")
        if self._duration_us(reference) != state.song.duration_us:
            raise MusicMapError("music-map song duration metadata changed")
        try:
            identity = verify_registered_media_bytes(path, reference.metadata)
        except MediaIntegrityError as exc:
            raise MusicMapError(str(exc)) from exc
        if identity.sha256 != state.song.sha256 or identity.size_bytes != state.song.size_bytes:
            raise MusicMapError("music-map song bytes no longer match registered identity")

    def _resolve_song(self, project_id: str, reference_id: str) -> tuple[ProjectReference, Any]:
        reference_id = _identifier(reference_id, field_name="song_reference_id")
        project = self.project_store.load_project(project_id)
        matches = [
            reference
            for reference in (*project.sources, *project.artifacts)
            if reference.id == reference_id and reference.kind == "audio"
        ]
        if len(matches) != 1:
            raise MusicMapError(
                f"song reference {reference_id!r} must identify exactly one project-owned audio file"
            )
        reference = matches[0]
        root = PurePosixPath(reference.path).parts[0]
        if root not in _MEDIA_ROOTS:
            raise MusicMapError(
                f"song reference {reference_id!r} uses unsupported project root {root!r}"
            )
        try:
            path = self.project_store.resolve_project_file(
                project_id,
                reference.path,
                must_exist=True,
                allowed_roots=(root,),
            )
        except ProjectValidationError as exc:
            raise MusicMapError(str(exc)) from exc
        return reference, path

    @staticmethod
    def _duration_us(reference: ProjectReference) -> int:
        value = reference.metadata.get("duration_us")
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise MusicMapError(
                f"audio reference {reference.id!r} requires positive duration_us metadata"
            )
        return value

    def _save(self, project_id: str, state: MusicMapState) -> None:
        try:
            self.project_store._atomic_write_json(self._path(project_id), state.to_dict())
        except OSError as exc:
            raise ProjectStoreError("could not persist music-map state") from exc
