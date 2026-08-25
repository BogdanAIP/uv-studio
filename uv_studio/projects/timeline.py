"""Canonical multitrack timeline state for Studio v2.

The JSON document under ``timeline/main.json`` is UV Studio-owned canonical
state. MLT, FFmpeg filtergraphs and frontend timeline stores are derived views;
they never become alternate mutation authorities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .models import ProjectDocument, ProjectReference, ProjectValidationError, validate_identifier
from .store import ProjectStore, ProjectStoreError

TIMELINE_SCHEMA_VERSION = 1
MAIN_TIMELINE_ID = "main"
MAIN_TIMELINE_PATH = "timeline/main.json"
_TIMELINE_TRACK_KINDS = frozenset({"video", "audio"})
_TIMELINE_INPUT_ROOTS = ("sources", "assets", "artifacts", "exports")
_MAX_TITLE_LENGTH = 200
_MAX_TIME_US = 7 * 24 * 60 * 60 * 1_000_000


class TimelineError(ProjectValidationError):
    """Invalid or inconsistent canonical Studio timeline state."""


class TimelineTrackNotFound(TimelineError):
    pass


class TimelineClipNotFound(TimelineError):
    pass


def _time_us(value: Any, *, field_name: str, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TimelineError(f"{field_name} must be an integer microsecond value")
    minimum = 1 if positive else 0
    if value < minimum or value > _MAX_TIME_US:
        comparator = "> 0" if positive else ">= 0"
        raise TimelineError(f"{field_name} must be {comparator} and <= {_MAX_TIME_US}")
    return value


def _title(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TimelineError(f"{field_name} must be non-empty text")
    normalized = value.strip()
    if len(normalized) > _MAX_TITLE_LENGTH:
        raise TimelineError(f"{field_name} must be <= {_MAX_TITLE_LENGTH} characters")
    return normalized


@dataclass(frozen=True)
class TimelineClip:
    clip_id: str
    reference_id: str
    timeline_start_us: int
    source_start_us: int
    duration_us: int
    enabled: bool = True
    muted: bool = False

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "clip_id", validate_identifier(self.clip_id, field_name="clip_id"))
            object.__setattr__(
                self,
                "reference_id",
                validate_identifier(self.reference_id, field_name="reference_id"),
            )
        except ProjectValidationError as exc:
            raise TimelineError(str(exc)) from exc
        object.__setattr__(
            self,
            "timeline_start_us",
            _time_us(self.timeline_start_us, field_name="timeline_start_us"),
        )
        object.__setattr__(
            self,
            "source_start_us",
            _time_us(self.source_start_us, field_name="source_start_us"),
        )
        object.__setattr__(
            self,
            "duration_us",
            _time_us(self.duration_us, field_name="duration_us", positive=True),
        )
        if not isinstance(self.enabled, bool):
            raise TimelineError("enabled must be boolean")
        if not isinstance(self.muted, bool):
            raise TimelineError("muted must be boolean")
        if self.timeline_end_us > _MAX_TIME_US:
            raise TimelineError("clip timeline end exceeds supported timeline bound")
        if self.source_end_us > _MAX_TIME_US:
            raise TimelineError("clip source end exceeds supported timeline bound")

    @property
    def timeline_end_us(self) -> int:
        return self.timeline_start_us + self.duration_us

    @property
    def source_end_us(self) -> int:
        return self.source_start_us + self.duration_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "reference_id": self.reference_id,
            "timeline_start_us": self.timeline_start_us,
            "source_start_us": self.source_start_us,
            "duration_us": self.duration_us,
            "enabled": self.enabled,
            "muted": self.muted,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TimelineClip":
        if not isinstance(data, Mapping):
            raise TimelineError("timeline clip must be a JSON object")
        allowed = {
            "clip_id",
            "reference_id",
            "timeline_start_us",
            "source_start_us",
            "duration_us",
            "enabled",
            "muted",
        }
        unknown = set(data).difference(allowed)
        if unknown:
            raise TimelineError(f"unsupported timeline clip fields: {sorted(unknown)!r}")
        required = {"clip_id", "reference_id", "timeline_start_us", "source_start_us", "duration_us"}
        missing = required.difference(data)
        if missing:
            raise TimelineError(f"timeline clip is missing fields: {sorted(missing)!r}")
        return cls(
            clip_id=data["clip_id"],
            reference_id=data["reference_id"],
            timeline_start_us=data["timeline_start_us"],
            source_start_us=data["source_start_us"],
            duration_us=data["duration_us"],
            enabled=data.get("enabled", True),
            muted=data.get("muted", False),
        )


@dataclass(frozen=True)
class TimelineTrack:
    track_id: str
    kind: str
    title: str
    clips: tuple[TimelineClip, ...] = ()
    enabled: bool = True
    muted: bool = False

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "track_id", validate_identifier(self.track_id, field_name="track_id"))
        except ProjectValidationError as exc:
            raise TimelineError(str(exc)) from exc
        if self.kind not in _TIMELINE_TRACK_KINDS:
            raise TimelineError(f"track kind must be one of {sorted(_TIMELINE_TRACK_KINDS)!r}")
        object.__setattr__(self, "title", _title(self.title, field_name="track title"))
        if not isinstance(self.enabled, bool):
            raise TimelineError("track enabled must be boolean")
        if not isinstance(self.muted, bool):
            raise TimelineError("track muted must be boolean")
        clips = tuple(self.clips)
        if not all(isinstance(clip, TimelineClip) for clip in clips):
            raise TimelineError("track clips must contain TimelineClip values")
        ids = [clip.clip_id for clip in clips]
        if len(ids) != len(set(ids)):
            raise TimelineError("clip_id values must be unique within a track")
        canonical = tuple(sorted(clips, key=lambda item: (item.timeline_start_us, item.clip_id)))
        previous: TimelineClip | None = None
        for clip in canonical:
            if previous is not None and clip.timeline_start_us < previous.timeline_end_us:
                raise TimelineError(
                    f"clips on track {self.track_id!r} must not overlap: "
                    f"{previous.clip_id!r} and {clip.clip_id!r}"
                )
            previous = clip
        object.__setattr__(self, "clips", canonical)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "kind": self.kind,
            "title": self.title,
            "enabled": self.enabled,
            "muted": self.muted,
            "clips": [clip.to_dict() for clip in self.clips],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TimelineTrack":
        if not isinstance(data, Mapping):
            raise TimelineError("timeline track must be a JSON object")
        allowed = {"track_id", "kind", "title", "enabled", "muted", "clips"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise TimelineError(f"unsupported timeline track fields: {sorted(unknown)!r}")
        required = {"track_id", "kind", "title"}
        missing = required.difference(data)
        if missing:
            raise TimelineError(f"timeline track is missing fields: {sorted(missing)!r}")
        raw_clips = data.get("clips", [])
        if not isinstance(raw_clips, list):
            raise TimelineError("timeline track clips must be a list")
        return cls(
            track_id=data["track_id"],
            kind=data["kind"],
            title=data["title"],
            enabled=data.get("enabled", True),
            muted=data.get("muted", False),
            clips=tuple(TimelineClip.from_dict(item) for item in raw_clips),
        )


@dataclass(frozen=True)
class TimelineDocument:
    timeline_id: str = MAIN_TIMELINE_ID
    tracks: tuple[TimelineTrack, ...] = ()
    schema_version: int = TIMELINE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TIMELINE_SCHEMA_VERSION:
            raise TimelineError(
                f"unsupported timeline schema {self.schema_version!r}; supported={TIMELINE_SCHEMA_VERSION}"
            )
        try:
            object.__setattr__(
                self,
                "timeline_id",
                validate_identifier(self.timeline_id, field_name="timeline_id"),
            )
        except ProjectValidationError as exc:
            raise TimelineError(str(exc)) from exc
        tracks = tuple(self.tracks)
        if not all(isinstance(track, TimelineTrack) for track in tracks):
            raise TimelineError("tracks must contain TimelineTrack values")
        track_ids = [track.track_id for track in tracks]
        if len(track_ids) != len(set(track_ids)):
            raise TimelineError("track_id values must be unique")
        clip_ids = [clip.clip_id for track in tracks for clip in track.clips]
        if len(clip_ids) != len(set(clip_ids)):
            raise TimelineError("clip_id values must be unique across the timeline")
        object.__setattr__(self, "tracks", tracks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timeline_id": self.timeline_id,
            "tracks": [track.to_dict() for track in self.tracks],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TimelineDocument":
        if not isinstance(data, Mapping):
            raise TimelineError("timeline document must be a JSON object")
        allowed = {"schema_version", "timeline_id", "tracks"}
        unknown = set(data).difference(allowed)
        if unknown:
            raise TimelineError(f"unsupported timeline fields: {sorted(unknown)!r}")
        if "schema_version" not in data:
            raise TimelineError("timeline document is missing schema_version")
        raw_tracks = data.get("tracks", [])
        if not isinstance(raw_tracks, list):
            raise TimelineError("timeline tracks must be a list")
        return cls(
            schema_version=data["schema_version"],
            timeline_id=data.get("timeline_id", MAIN_TIMELINE_ID),
            tracks=tuple(TimelineTrack.from_dict(item) for item in raw_tracks),
        )

    def track(self, track_id: str) -> TimelineTrack:
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        raise TimelineTrackNotFound(track_id)

    def locate_clip(self, clip_id: str) -> tuple[TimelineTrack, TimelineClip]:
        for track in self.tracks:
            for clip in track.clips:
                if clip.clip_id == clip_id:
                    return track, clip
        raise TimelineClipNotFound(clip_id)


@dataclass(frozen=True)
class TimelineReference:
    reference: ProjectReference
    path: Path


class TimelineStore:
    """Atomic persistence and project-reference validation for the main timeline."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store

    def _path(self, project_id: str, *, must_exist: bool = False) -> Path:
        try:
            return self.project_store.resolve_project_file(
                project_id,
                MAIN_TIMELINE_PATH,
                must_exist=must_exist,
                allowed_roots=("timeline",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise TimelineError(str(exc)) from exc

    def load(self, project_id: str, *, validate_references: bool = False) -> TimelineDocument:
        self.project_store.load_project(project_id)
        path = self._path(project_id)
        if not path.exists():
            return TimelineDocument()
        if not path.is_file() or path.is_symlink():
            raise TimelineError("timeline path must be a regular project file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TimelineError("timeline document is malformed JSON") from exc
        except OSError as exc:
            raise TimelineError("timeline document could not be read") from exc
        timeline = TimelineDocument.from_dict(data)
        if timeline.timeline_id != MAIN_TIMELINE_ID:
            raise TimelineError("timeline/main.json must contain timeline_id='main'")
        if validate_references:
            self._validate_references(project_id, timeline)
        return timeline

    def validate(
        self,
        project_id: str,
        timeline: TimelineDocument,
        *,
        project: "ProjectDocument | None" = None,
    ) -> TimelineDocument:
        if not isinstance(timeline, TimelineDocument):
            raise TimelineError("timeline validation requires TimelineDocument")
        if timeline.timeline_id != MAIN_TIMELINE_ID:
            raise TimelineError("only the main timeline is supported in schema v1")
        canonical_project = project or self.project_store.load_project(project_id)
        if canonical_project.project_id != project_id:
            raise TimelineError("timeline project identity does not match project_id")
        self._validate_references(project_id, timeline, project=canonical_project)
        return timeline

    def save(self, project_id: str, timeline: TimelineDocument) -> TimelineDocument:
        if not isinstance(timeline, TimelineDocument):
            raise TimelineError("save requires TimelineDocument")
        if timeline.timeline_id != MAIN_TIMELINE_ID:
            raise TimelineError("only the main timeline is supported in schema v1")
        with self.project_store._lock:
            self.project_store.load_project(project_id)
            self.validate(project_id, timeline)
            self.project_store._atomic_write_json(self._path(project_id), timeline.to_dict())
        return timeline

    def reference(
        self,
        project_id: str,
        reference_id: str,
        *,
        project: "ProjectDocument | None" = None,
    ) -> TimelineReference:
        project = project or self.project_store.load_project(project_id)
        reference = next(
            (item for item in (*project.sources, *project.artifacts) if item.id == reference_id),
            None,
        )
        if reference is None:
            raise TimelineError(f"timeline reference is not registered in project: {reference_id!r}")
        try:
            path = self.project_store.resolve_project_file(
                project_id,
                reference.path,
                must_exist=True,
                allowed_roots=_TIMELINE_INPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise TimelineError(str(exc)) from exc
        if not path.is_file() or path.is_symlink():
            raise TimelineError(f"timeline reference must resolve to a regular project file: {reference_id!r}")
        return TimelineReference(reference=reference, path=path)

    def _validate_references(
        self,
        project_id: str,
        timeline: TimelineDocument,
        *,
        project: "ProjectDocument | None" = None,
    ) -> None:
        resolved: dict[str, TimelineReference] = {}
        for track in timeline.tracks:
            for clip in track.clips:
                item = resolved.get(clip.reference_id)
                if item is None:
                    item = self.reference(project_id, clip.reference_id, project=project)
                    resolved[clip.reference_id] = item
                reference = item.reference
                if track.kind == "video" and reference.kind not in {"video", "image"}:
                    raise TimelineError(
                        f"video track {track.track_id!r} requires image/video references; "
                        f"{reference.id!r} is {reference.kind!r}"
                    )
                if track.kind == "audio" and reference.kind != "audio":
                    raise TimelineError(
                        f"audio track {track.track_id!r} requires audio references; "
                        f"{reference.id!r} is {reference.kind!r}"
                    )
                if reference.kind == "image":
                    if clip.source_start_us != 0:
                        raise TimelineError("still-image clips require source_start_us=0")
                    continue
                duration = reference.metadata.get("duration_us")
                if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
                    raise TimelineError(
                        f"timed media reference {reference.id!r} is missing positive duration_us"
                    )
                if clip.source_end_us > duration:
                    raise TimelineError(
                        f"clip {clip.clip_id!r} exceeds source duration for {reference.id!r}"
                    )
