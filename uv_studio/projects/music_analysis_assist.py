"""Ephemeral, provider-neutral song/lyrics/structure analysis assistance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import compatibility_recipe_id
from .music_map import (
    MAX_LYRIC_PHRASES,
    MAX_MUSIC_MARKERS,
    MAX_MUSIC_SECTIONS,
    MusicExcerpt,
    MusicLyricPhrase,
    MusicMapError,
    MusicMapStore,
    MusicSection,
    MusicTimingMarker,
)
from .source_media import ProjectSourceMediaStore, SourceMediaError
from .store import ProjectStore

MUSIC_ANALYSIS_ASSIST_SCHEMA_VERSION = 1
MUSIC_ANALYSIS_ASSIST_CAPABILITY_ID = "audio.analyze_music"


class MusicAnalysisAssistError(MusicMapError):
    """Invalid, stale or unsafe non-canonical music-analysis suggestion."""


@dataclass(frozen=True)
class MusicAnalysisBinding:
    song_reference_id: str
    song_reference_path: str
    song_sha256: str
    song_size_bytes: int
    song_duration_us: int
    current_music_map_revision_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "song_reference_id": self.song_reference_id,
            "song_reference_path": self.song_reference_path,
            "song_sha256": self.song_sha256,
            "song_size_bytes": self.song_size_bytes,
            "song_duration_us": self.song_duration_us,
            "current_music_map_revision_sha256": self.current_music_map_revision_sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MusicAnalysisBinding":
        if not isinstance(data, Mapping):
            raise MusicAnalysisAssistError("music-analysis binding must be an object")
        allowed = {
            "song_reference_id", "song_reference_path", "song_sha256", "song_size_bytes",
            "song_duration_us", "current_music_map_revision_sha256",
        }
        if set(data) != allowed:
            raise MusicAnalysisAssistError("music-analysis binding fields do not match schema")
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class MusicAnalysisAssistPackage:
    binding: MusicAnalysisBinding
    capability_input: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": MUSIC_ANALYSIS_ASSIST_SCHEMA_VERSION,
            "capability_id": MUSIC_ANALYSIS_ASSIST_CAPABILITY_ID,
            "binding": self.binding.to_dict(),
            "capability_input": self.capability_input,
            "requires_human_confirmation": True,
            "canonical_state_mutated": False,
        }


def _binding(store: ProjectStore, project_id: str, song_reference_id: str) -> MusicAnalysisBinding:
    project = store.load_project(project_id)
    if compatibility_recipe_id(project) != "music_video":
        raise MusicAnalysisAssistError("music analysis assist is only valid for music_video")
    try:
        reference, _path = ProjectSourceMediaStore(store).resolve_verified(
            project_id, song_reference_id, expected_kind="audio"
        )
    except SourceMediaError as exc:
        raise MusicAnalysisAssistError(str(exc)) from exc
    metadata = reference.metadata
    sha = metadata.get("sha256")
    size = metadata.get("size_bytes")
    duration = metadata.get("duration_us")
    if not isinstance(sha, str) or len(sha) != 64 or not isinstance(size, int) or size <= 0:
        raise MusicAnalysisAssistError("song source is missing integrity metadata")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise MusicAnalysisAssistError("song source is missing positive duration")
    current = MusicMapStore(store).load(project_id, validate_current=True)
    current_revision = None
    if current is not None:
        if current.song.reference_id != reference.id:
            current_revision = None
        else:
            current_revision = current.revision_sha256
    return MusicAnalysisBinding(
        song_reference_id=reference.id,
        song_reference_path=reference.path,
        song_sha256=sha.lower(),
        song_size_bytes=size,
        song_duration_us=duration,
        current_music_map_revision_sha256=current_revision,
    )


def build_music_analysis_assist(
    store: ProjectStore, project_id: str, *, song_reference_id: str
) -> MusicAnalysisAssistPackage:
    binding = _binding(store, project_id, song_reference_id)
    return MusicAnalysisAssistPackage(
        binding=binding,
        capability_input={
            "task": "music_structure_lyrics_timing_analysis",
            "binding": binding.to_dict(),
            "audio": {
                "project_reference": binding.song_reference_path,
                "sha256": binding.song_sha256,
                "duration_us": binding.song_duration_us,
            },
            "requested_output": {
                "excerpt": {"start_us": "integer", "end_us": "integer"},
                "sections": {"max_items": MAX_MUSIC_SECTIONS},
                "markers": {"max_items": MAX_MUSIC_MARKERS},
                "lyric_phrases": {"max_items": MAX_LYRIC_PHRASES},
                "note": "optional concise analysis note",
            },
            "instructions": (
                "Suggest song structure, rhythm/semantic markers and lyric phrases only from the "
                "bound audio. Return timestamps in microseconds. This output is advisory; do not "
                "claim that Music Map was changed or accepted."
            ),
        },
    )


def normalize_music_analysis_suggestion(
    store: ProjectStore,
    project_id: str,
    *,
    song_reference_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise MusicAnalysisAssistError("music-analysis suggestion must be an object")
    allowed = {"binding", "excerpt", "sections", "markers", "lyric_phrases", "note"}
    if set(payload) != allowed:
        raise MusicAnalysisAssistError("music-analysis suggestion fields do not match schema")
    current = build_music_analysis_assist(
        store, project_id, song_reference_id=song_reference_id
    )
    supplied = MusicAnalysisBinding.from_dict(payload["binding"])
    if supplied != current.binding:
        raise MusicAnalysisAssistError("music-analysis suggestion is stale or bound to another song")
    excerpt = MusicExcerpt.from_dict(payload["excerpt"])
    if excerpt.end_us > supplied.song_duration_us:
        raise MusicAnalysisAssistError("suggested excerpt exceeds bound song duration")
    raw_sections = payload["sections"]
    raw_markers = payload["markers"]
    raw_lyrics = payload["lyric_phrases"]
    if not isinstance(raw_sections, list) or len(raw_sections) > MAX_MUSIC_SECTIONS:
        raise MusicAnalysisAssistError("invalid suggested music sections")
    if not isinstance(raw_markers, list) or len(raw_markers) > MAX_MUSIC_MARKERS:
        raise MusicAnalysisAssistError("invalid suggested music markers")
    if not isinstance(raw_lyrics, list) or len(raw_lyrics) > MAX_LYRIC_PHRASES:
        raise MusicAnalysisAssistError("invalid suggested lyric phrases")
    sections = tuple(MusicSection.from_dict(item) for item in raw_sections)
    markers = tuple(MusicTimingMarker.from_dict(item) for item in raw_markers)
    lyrics = tuple(MusicLyricPhrase.from_dict(item) for item in raw_lyrics)
    for item in sections:
        if item.start_us < excerpt.start_us or item.end_us > excerpt.end_us:
            raise MusicAnalysisAssistError("suggested section lies outside suggested excerpt")
    for item in markers:
        if item.time_us < excerpt.start_us or item.time_us > excerpt.end_us:
            raise MusicAnalysisAssistError("suggested marker lies outside suggested excerpt")
    for item in lyrics:
        if item.start_us < excerpt.start_us or item.end_us > excerpt.end_us:
            raise MusicAnalysisAssistError("suggested lyric phrase lies outside suggested excerpt")
    for values, label in ((sections, "section"), (markers, "marker"), (lyrics, "lyric phrase")):
        ids = [getattr(item, "section_id", getattr(item, "marker_id", getattr(item, "phrase_id", None))) for item in values]
        if len(ids) != len(set(ids)):
            raise MusicAnalysisAssistError(f"suggested {label} IDs must be unique")
    note = payload["note"]
    if note is not None and (not isinstance(note, str) or not note.strip() or len(note.strip()) > 4000):
        raise MusicAnalysisAssistError("music-analysis note must be non-empty <= 4000 chars or null")
    return {
        "binding": supplied.to_dict(),
        "excerpt": excerpt.to_dict(),
        "sections": [item.to_dict() for item in sections],
        "markers": [item.to_dict() for item in markers],
        "lyric_phrases": [item.to_dict() for item in lyrics],
        "note": None if note is None else note.strip(),
        "requires_human_confirmation": True,
        "canonical_state_mutated": False,
    }
