"""Studio timeline commands shared by GUI, Agent, scripts and MCP callers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from typing import Any

from uv_studio.projects.models import ProjectValidationError, validate_identifier
from uv_studio.projects.timeline import (
    TimelineClip,
    TimelineClipNotFound,
    TimelineDocument,
    TimelineError,
    TimelineStore,
    TimelineTrack,
    TimelineTrackNotFound,
)
from uv_studio.projects.store import ProjectStore


class TimelineCommandError(ProjectValidationError):
    """A requested Studio timeline mutation is invalid."""


def _optional_identifier(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return validate_identifier(value, field_name=field_name)
    except ProjectValidationError as exc:
        raise TimelineCommandError(str(exc)) from exc


@dataclass(frozen=True)
class CreateTrackCommand:
    kind: str
    title: str | None = None
    track_id: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"video", "audio"}:
            raise TimelineCommandError("kind must be 'video' or 'audio'")
        object.__setattr__(self, "track_id", _optional_identifier(self.track_id, field_name="track_id"))
        if self.title is not None:
            if not isinstance(self.title, str) or not self.title.strip():
                raise TimelineCommandError("title must be non-empty text when provided")
            if len(self.title.strip()) > 200:
                raise TimelineCommandError("title must be <= 200 characters")
            object.__setattr__(self, "title", self.title.strip())


@dataclass(frozen=True)
class AddClipCommand:
    track_id: str
    reference_id: str
    timeline_start_us: int
    duration_us: int
    source_start_us: int = 0
    clip_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("track_id", "reference_id"):
            try:
                object.__setattr__(
                    self,
                    field_name,
                    validate_identifier(getattr(self, field_name), field_name=field_name),
                )
            except ProjectValidationError as exc:
                raise TimelineCommandError(str(exc)) from exc
        object.__setattr__(self, "clip_id", _optional_identifier(self.clip_id, field_name="clip_id"))
        # TimelineClip owns exact time validation; instantiate only after IDs normalize.
        try:
            TimelineClip(
                clip_id=self.clip_id or "clip_validation",
                reference_id=self.reference_id,
                timeline_start_us=self.timeline_start_us,
                source_start_us=self.source_start_us,
                duration_us=self.duration_us,
            )
        except TimelineError as exc:
            raise TimelineCommandError(str(exc)) from exc


@dataclass(frozen=True)
class MoveClipCommand:
    clip_id: str
    timeline_start_us: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "clip_id", validate_identifier(self.clip_id, field_name="clip_id"))
        except ProjectValidationError as exc:
            raise TimelineCommandError(str(exc)) from exc
        if isinstance(self.timeline_start_us, bool) or not isinstance(self.timeline_start_us, int) or self.timeline_start_us < 0:
            raise TimelineCommandError("timeline_start_us must be a non-negative integer microsecond value")


@dataclass(frozen=True)
class TrimClipCommand:
    clip_id: str
    source_start_us: int
    duration_us: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "clip_id", validate_identifier(self.clip_id, field_name="clip_id"))
        except ProjectValidationError as exc:
            raise TimelineCommandError(str(exc)) from exc
        if isinstance(self.source_start_us, bool) or not isinstance(self.source_start_us, int) or self.source_start_us < 0:
            raise TimelineCommandError("source_start_us must be a non-negative integer microsecond value")
        if isinstance(self.duration_us, bool) or not isinstance(self.duration_us, int) or self.duration_us <= 0:
            raise TimelineCommandError("duration_us must be a positive integer microsecond value")


@dataclass(frozen=True)
class RemoveClipCommand:
    clip_id: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "clip_id", validate_identifier(self.clip_id, field_name="clip_id"))
        except ProjectValidationError as exc:
            raise TimelineCommandError(str(exc)) from exc


@dataclass(frozen=True)
class TimelineCommandResult:
    command: str
    timeline: TimelineDocument
    track_id: str | None = None
    clip_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "track_id": self.track_id,
            "clip_id": self.clip_id,
            "timeline": self.timeline.to_dict(),
        }


class TimelineCommandService:
    """Single mutation authority for the canonical Studio timeline."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.timelines = TimelineStore(project_store)

    @staticmethod
    def _new_track_id() -> str:
        return f"trk_{uuid.uuid4().hex}"

    @staticmethod
    def _new_clip_id() -> str:
        return f"clip_{uuid.uuid4().hex}"

    @staticmethod
    def _default_track_title(timeline: TimelineDocument, kind: str) -> str:
        count = sum(track.kind == kind for track in timeline.tracks) + 1
        return f"{'Video' if kind == 'video' else 'Audio'} {count}"

    @staticmethod
    def _replace_track(
        timeline: TimelineDocument,
        track_id: str,
        replacement: TimelineTrack,
    ) -> TimelineDocument:
        tracks = tuple(replacement if track.track_id == track_id else track for track in timeline.tracks)
        return TimelineDocument(timeline_id=timeline.timeline_id, tracks=tracks)

    def create_track(self, project_id: str, command: CreateTrackCommand) -> TimelineCommandResult:
        if not isinstance(command, CreateTrackCommand):
            raise TimelineCommandError("create_track requires CreateTrackCommand")
        timeline = self.timelines.load(project_id)
        track_id = command.track_id or self._new_track_id()
        if any(track.track_id == track_id for track in timeline.tracks):
            raise TimelineCommandError(f"track already exists: {track_id!r}")
        track = TimelineTrack(
            track_id=track_id,
            kind=command.kind,
            title=command.title or self._default_track_title(timeline, command.kind),
        )
        updated = TimelineDocument(
            timeline_id=timeline.timeline_id,
            tracks=(*timeline.tracks, track),
        )
        try:
            self.timelines.save(project_id, updated)
        except TimelineError as exc:
            raise TimelineCommandError(str(exc)) from exc
        return TimelineCommandResult(command="create_track", track_id=track_id, timeline=updated)

    def add_clip(self, project_id: str, command: AddClipCommand) -> TimelineCommandResult:
        if not isinstance(command, AddClipCommand):
            raise TimelineCommandError("add_clip requires AddClipCommand")
        timeline = self.timelines.load(project_id)
        try:
            track = timeline.track(command.track_id)
        except TimelineTrackNotFound as exc:
            raise TimelineCommandError(f"track not found: {command.track_id!r}") from exc
        clip_id = command.clip_id or self._new_clip_id()
        if any(clip.clip_id == clip_id for item in timeline.tracks for clip in item.clips):
            raise TimelineCommandError(f"clip already exists: {clip_id!r}")
        clip = TimelineClip(
            clip_id=clip_id,
            reference_id=command.reference_id,
            timeline_start_us=command.timeline_start_us,
            source_start_us=command.source_start_us,
            duration_us=command.duration_us,
        )
        try:
            replacement = replace(track, clips=(*track.clips, clip))
            updated = self._replace_track(timeline, track.track_id, replacement)
            self.timelines.save(project_id, updated)
        except TimelineError as exc:
            raise TimelineCommandError(str(exc)) from exc
        return TimelineCommandResult(
            command="add_clip",
            track_id=track.track_id,
            clip_id=clip_id,
            timeline=updated,
        )

    def move_clip(self, project_id: str, command: MoveClipCommand) -> TimelineCommandResult:
        if not isinstance(command, MoveClipCommand):
            raise TimelineCommandError("move_clip requires MoveClipCommand")
        timeline = self.timelines.load(project_id)
        try:
            track, clip = timeline.locate_clip(command.clip_id)
        except TimelineClipNotFound as exc:
            raise TimelineCommandError(f"clip not found: {command.clip_id!r}") from exc
        moved = replace(clip, timeline_start_us=command.timeline_start_us)
        try:
            replacement = replace(
                track,
                clips=tuple(moved if item.clip_id == clip.clip_id else item for item in track.clips),
            )
            updated = self._replace_track(timeline, track.track_id, replacement)
            self.timelines.save(project_id, updated)
        except TimelineError as exc:
            raise TimelineCommandError(str(exc)) from exc
        return TimelineCommandResult(
            command="move_clip",
            track_id=track.track_id,
            clip_id=clip.clip_id,
            timeline=updated,
        )

    def trim_clip(self, project_id: str, command: TrimClipCommand) -> TimelineCommandResult:
        if not isinstance(command, TrimClipCommand):
            raise TimelineCommandError("trim_clip requires TrimClipCommand")
        timeline = self.timelines.load(project_id)
        try:
            track, clip = timeline.locate_clip(command.clip_id)
        except TimelineClipNotFound as exc:
            raise TimelineCommandError(f"clip not found: {command.clip_id!r}") from exc
        trimmed = replace(
            clip,
            source_start_us=command.source_start_us,
            duration_us=command.duration_us,
        )
        try:
            replacement = replace(
                track,
                clips=tuple(trimmed if item.clip_id == clip.clip_id else item for item in track.clips),
            )
            updated = self._replace_track(timeline, track.track_id, replacement)
            self.timelines.save(project_id, updated)
        except TimelineError as exc:
            raise TimelineCommandError(str(exc)) from exc
        return TimelineCommandResult(
            command="trim_clip",
            track_id=track.track_id,
            clip_id=clip.clip_id,
            timeline=updated,
        )

    def remove_clip(self, project_id: str, command: RemoveClipCommand) -> TimelineCommandResult:
        if not isinstance(command, RemoveClipCommand):
            raise TimelineCommandError("remove_clip requires RemoveClipCommand")
        timeline = self.timelines.load(project_id)
        try:
            track, clip = timeline.locate_clip(command.clip_id)
        except TimelineClipNotFound as exc:
            raise TimelineCommandError(f"clip not found: {command.clip_id!r}") from exc
        try:
            replacement = replace(
                track,
                clips=tuple(item for item in track.clips if item.clip_id != clip.clip_id),
            )
            updated = self._replace_track(timeline, track.track_id, replacement)
            self.timelines.save(project_id, updated)
        except TimelineError as exc:
            raise TimelineCommandError(str(exc)) from exc
        return TimelineCommandResult(
            command="remove_clip",
            track_id=track.track_id,
            clip_id=clip.clip_id,
            timeline=updated,
        )
