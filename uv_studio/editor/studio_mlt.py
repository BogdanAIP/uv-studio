"""Derived MLT projection for the canonical Studio v2 multitrack timeline."""

from __future__ import annotations

import math
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectStore, ProjectStoreError
from uv_studio.projects.timeline import TimelineDocument, TimelineReference, TimelineStore, TimelineTrack

_MICROSECONDS_PER_SECOND = 1_000_000
_DEFAULT_RATE = Fraction(30, 1)
_DEFAULT_WIDTH = 1920
_DEFAULT_HEIGHT = 1080


class StudioMLTError(ProjectValidationError):
    """Canonical Studio timeline cannot be projected safely into MLT."""


def _positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise StudioMLTError(f"{field_name} must be a positive integer")
    return value


def _parse_rate(value: Any) -> Fraction:
    if value in (None, "", "N/A"):
        return _DEFAULT_RATE
    if not isinstance(value, str):
        raise StudioMLTError("avg_frame_rate must be a ratio string")
    try:
        rate = Fraction(value.strip())
    except (ValueError, ZeroDivisionError) as exc:
        raise StudioMLTError("avg_frame_rate is invalid") from exc
    if rate <= 0 or rate > 1000:
        raise StudioMLTError("avg_frame_rate is outside supported bounds")
    return rate


def _frame(time_us: int, rate: Fraction) -> int:
    return round(Fraction(time_us, _MICROSECONDS_PER_SECOND) * rate)


def _frame_error_us(time_us: int, frame: int, rate: Fraction) -> int:
    represented = Fraction(frame * _MICROSECONDS_PER_SECOND, 1) / rate
    return round(abs(represented - time_us))


def _add_property(parent: ET.Element, name: str, value: str) -> None:
    node = ET.SubElement(parent, "property", {"name": name})
    node.text = value


@dataclass(frozen=True)
class StudioMLTClipProjection:
    track_id: str
    clip_id: str
    reference_id: str
    media_kind: str
    producer_id: str
    timeline_start_frame: int
    source_in_frame: int
    source_out_frame: int
    duration_frames: int
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "clip_id": self.clip_id,
            "reference_id": self.reference_id,
            "media_kind": self.media_kind,
            "timeline_start_frame": self.timeline_start_frame,
            "source_in_frame": self.source_in_frame,
            "source_out_frame": self.source_out_frame,
            "duration_frames": self.duration_frames,
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class StudioMLTTrackProjection:
    track_id: str
    kind: str
    enabled: bool
    muted: bool
    clips: tuple[StudioMLTClipProjection, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "kind": self.kind,
            "enabled": self.enabled,
            "muted": self.muted,
            "clips": [clip.to_dict() for clip in self.clips],
        }


@dataclass(frozen=True)
class StudioMLTProjection:
    timeline_id: str
    frame_rate_num: int
    frame_rate_den: int
    width: int
    height: int
    duration_us: int
    duration_frames: int
    max_boundary_error_us: int
    tracks: tuple[StudioMLTTrackProjection, ...]
    xml_text: str

    @property
    def exact_boundaries(self) -> bool:
        return self.max_boundary_error_us == 0

    def to_summary(self) -> dict[str, Any]:
        return {
            "adapter_id": "mlt",
            "timeline_id": self.timeline_id,
            "frame_rate": f"{self.frame_rate_num}/{self.frame_rate_den}",
            "width": self.width,
            "height": self.height,
            "duration_us": self.duration_us,
            "duration_frames": self.duration_frames,
            "exact_boundaries": self.exact_boundaries,
            "max_boundary_error_us": self.max_boundary_error_us,
            "tracks": [track.to_dict() for track in self.tracks],
        }


@dataclass(frozen=True)
class _PreparedClip:
    track: TimelineTrack
    reference_info: TimelineReference
    producer_id: str
    timeline_start_frame: int
    source_in_frame: int
    source_out_frame: int
    duration_frames: int
    producer_length: int
    enabled: bool


class StudioMLTTimelineAdapter:
    """Project ``timeline/main.json`` into ephemeral MLT XML.

    Resolved host paths appear only inside ``xml_text`` for the local engine.
    ``to_summary`` intentionally exposes project/reference identities instead.
    """

    adapter_id = "mlt"

    def __init__(self, project_store: ProjectStore, *, melt_path: str | None = None) -> None:
        self.project_store = project_store
        self.timelines = TimelineStore(project_store)
        self.melt_path = melt_path

    def runtime_path(self) -> str | None:
        return self.melt_path or shutil.which("melt") or shutil.which("melt.exe")

    def runtime_available(self) -> bool:
        return self.runtime_path() is not None

    def _references(self, project_id: str) -> dict[str, ProjectReference]:
        project = self.project_store.load_project(project_id)
        return {item.id: item for item in (*project.sources, *project.artifacts)}

    @staticmethod
    def _profile(
        timeline: TimelineDocument,
        references: dict[str, ProjectReference],
    ) -> tuple[Fraction, int, int]:
        visual_refs: list[ProjectReference] = []
        for track in timeline.tracks:
            if track.kind != "video":
                continue
            for clip in track.clips:
                reference = references.get(clip.reference_id)
                if reference is not None and reference.kind in {"video", "image"}:
                    visual_refs.append(reference)
        if not visual_refs:
            return _DEFAULT_RATE, _DEFAULT_WIDTH, _DEFAULT_HEIGHT

        first = visual_refs[0]
        width = _positive_int(first.metadata.get("width"), field_name=f"{first.id}.width")
        height = _positive_int(first.metadata.get("height"), field_name=f"{first.id}.height")

        video_refs = [reference for reference in visual_refs if reference.kind == "video"]
        rate = _parse_rate(video_refs[0].metadata.get("avg_frame_rate")) if video_refs else _DEFAULT_RATE
        for reference in video_refs[1:]:
            candidate = _parse_rate(reference.metadata.get("avg_frame_rate"))
            if candidate != rate:
                raise StudioMLTError(
                    "Studio v2 MLT projection currently requires one project frame rate; "
                    f"{reference.id!r} has {candidate} instead of {rate}"
                )
        return rate, width, height

    def project(self, project_id: str) -> StudioMLTProjection:
        try:
            timeline = self.timelines.load(project_id, validate_references=True)
            references = self._references(project_id)
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise StudioMLTError(str(exc)) from exc

        rate, width, height = self._profile(timeline, references)
        all_clips = [clip for track in timeline.tracks for clip in track.clips]
        duration_us = max((clip.timeline_end_us for clip in all_clips), default=0)
        duration_frames = max(_frame(duration_us, rate), 1)
        boundary_errors: list[int] = []

        prepared_by_track: dict[str, list[_PreparedClip]] = {}
        producer_index = 0
        for track in timeline.tracks:
            cursor_frame = 0
            prepared: list[_PreparedClip] = []
            for clip in track.clips:
                reference_info = self.timelines.reference(project_id, clip.reference_id)
                reference = reference_info.reference
                producer_index += 1
                producer_id = f"uv_studio_producer_{producer_index}"
                start_frame = _frame(clip.timeline_start_us, rate)
                source_in_frame = _frame(clip.source_start_us, rate)
                duration_frame_count = max(_frame(clip.duration_us, rate), 1)
                source_out_frame = source_in_frame + duration_frame_count - 1
                boundary_errors.extend(
                    (
                        _frame_error_us(clip.timeline_start_us, start_frame, rate),
                        _frame_error_us(clip.source_start_us, source_in_frame, rate),
                        _frame_error_us(clip.duration_us, duration_frame_count, rate),
                    )
                )
                if start_frame < cursor_frame:
                    raise StudioMLTError(
                        f"clip {clip.clip_id!r} overlaps a previous clip after frame conversion"
                    )
                producer_length = duration_frame_count
                if reference.kind != "image":
                    source_duration = _positive_int(
                        reference.metadata.get("duration_us"),
                        field_name=f"{reference.id}.duration_us",
                    )
                    producer_length = max(_frame(source_duration, rate), source_out_frame + 1)
                enabled = clip.enabled and track.enabled
                if track.kind == "audio" and (track.muted or clip.muted):
                    enabled = False
                prepared.append(
                    _PreparedClip(
                        track=track,
                        reference_info=reference_info,
                        producer_id=producer_id,
                        timeline_start_frame=start_frame,
                        source_in_frame=source_in_frame,
                        source_out_frame=source_out_frame,
                        duration_frames=duration_frame_count,
                        producer_length=producer_length,
                        enabled=enabled,
                    )
                )
                cursor_frame = start_frame + duration_frame_count
            prepared_by_track[track.track_id] = prepared

        root = ET.Element("mlt", {"LC_NUMERIC": "C"})
        gcd_width_height = math.gcd(width, height)
        ET.SubElement(
            root,
            "profile",
            {
                "description": "UV Studio v2 derived multitrack projection",
                "width": str(width),
                "height": str(height),
                "progressive": "1",
                "sample_aspect_num": "1",
                "sample_aspect_den": "1",
                "display_aspect_num": str(width // gcd_width_height),
                "display_aspect_den": str(height // gcd_width_height),
                "frame_rate_num": str(rate.numerator),
                "frame_rate_den": str(rate.denominator),
                "colorspace": "709",
            },
        )

        # MLT resolves playlist producer references while parsing. Declare every
        # producer before every playlist; forward references are not safe.
        for track in timeline.tracks:
            for prepared in prepared_by_track[track.track_id]:
                producer = ET.SubElement(
                    root,
                    "producer",
                    {
                        "id": prepared.producer_id,
                        "in": "0",
                        "out": str(prepared.producer_length - 1),
                    },
                )
                _add_property(producer, "mlt_service", "avformat-novalidate")
                _add_property(
                    producer,
                    "resource",
                    prepared.reference_info.path.resolve().as_posix(),
                )
                _add_property(producer, "length", str(prepared.producer_length))

        track_projections: list[StudioMLTTrackProjection] = []
        playlist_ids: list[tuple[str, str]] = []
        for track_index, track in enumerate(timeline.tracks, start=1):
            playlist_id = f"uv_studio_playlist_{track_index}"
            playlist = ET.SubElement(root, "playlist", {"id": playlist_id})
            playlist_ids.append((playlist_id, track.kind))
            cursor_frame = 0
            projected_clips: list[StudioMLTClipProjection] = []
            source_clips = {clip.clip_id: clip for clip in track.clips}

            for prepared in prepared_by_track[track.track_id]:
                clip = next(
                    item
                    for item in track.clips
                    if _frame(item.timeline_start_us, rate) == prepared.timeline_start_frame
                    and item.reference_id == prepared.reference_info.reference.id
                    and item.clip_id in source_clips
                )
                if prepared.timeline_start_frame > cursor_frame:
                    ET.SubElement(
                        playlist,
                        "blank",
                        {"length": str(prepared.timeline_start_frame - cursor_frame)},
                    )
                if prepared.enabled:
                    ET.SubElement(
                        playlist,
                        "entry",
                        {
                            "producer": prepared.producer_id,
                            "in": str(prepared.source_in_frame),
                            "out": str(prepared.source_out_frame),
                            "uv_clip_id": clip.clip_id,
                        },
                    )
                else:
                    ET.SubElement(
                        playlist,
                        "blank",
                        {"length": str(prepared.duration_frames)},
                    )
                cursor_frame = prepared.timeline_start_frame + prepared.duration_frames
                projected_clips.append(
                    StudioMLTClipProjection(
                        track_id=track.track_id,
                        clip_id=clip.clip_id,
                        reference_id=clip.reference_id,
                        media_kind=prepared.reference_info.reference.kind,
                        producer_id=prepared.producer_id,
                        timeline_start_frame=prepared.timeline_start_frame,
                        source_in_frame=prepared.source_in_frame,
                        source_out_frame=prepared.source_out_frame,
                        duration_frames=prepared.duration_frames,
                        enabled=prepared.enabled,
                    )
                )

            track_projections.append(
                StudioMLTTrackProjection(
                    track_id=track.track_id,
                    kind=track.kind,
                    enabled=track.enabled,
                    muted=track.muted,
                    clips=tuple(projected_clips),
                )
            )

        tractor = ET.SubElement(
            root,
            "tractor",
            {"id": "uv_studio_tractor", "in": "0", "out": str(duration_frames - 1)},
        )
        for playlist_id, kind in playlist_ids:
            # Video tracks contribute picture only; audio tracks contribute sound only.
            ET.SubElement(
                tractor,
                "track",
                {"producer": playlist_id, "hide": "audio" if kind == "video" else "video"},
            )

        return StudioMLTProjection(
            timeline_id=timeline.timeline_id,
            frame_rate_num=rate.numerator,
            frame_rate_den=rate.denominator,
            width=width,
            height=height,
            duration_us=duration_us,
            duration_frames=duration_frames,
            max_boundary_error_us=max(boundary_errors, default=0),
            tracks=tuple(track_projections),
            xml_text=ET.tostring(root, encoding="unicode"),
        )

    def project_summary(self, project_id: str) -> dict[str, Any]:
        projection = self.project(project_id)
        return {
            **projection.to_summary(),
            "runtime_available": self.runtime_available(),
        }
