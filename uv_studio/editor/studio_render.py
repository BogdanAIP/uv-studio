"""Deterministic first Studio v2 export from the canonical multitrack timeline.

The initial renderer is intentionally bounded: one active visual track, optional
single active audio clip, no timeline gaps or visual overlays. Broader NLE
composition remains an MLT/application-layer expansion rather than silent best
effort here.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import CapabilityToolFailed
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectStore, ProjectStoreError
from uv_studio.projects.timeline import TimelineClip, TimelineError, TimelineStore, TimelineTrack

from .studio_mlt import StudioMLTError, StudioMLTTimelineAdapter

_DURATION_TOLERANCE_US = 250_000


class StudioRenderError(ProjectValidationError):
    """Canonical Studio timeline cannot be rendered by the bounded first renderer."""


def _revision_sha256(timeline: dict[str, Any]) -> str:
    payload = json.dumps(
        timeline,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _concat_quote(path: Path) -> str:
    value = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{value}'\n"


def _fps_expression(num: int, den: int) -> str:
    return str(num) if den == 1 else f"{num}/{den}"


def _video_filter(width: int, height: int, fps_num: int, fps_den: int) -> str:
    return (
        f"fps={_fps_expression(fps_num, fps_den)},"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,format=yuv420p"
    )


@dataclass(frozen=True)
class StudioRenderResult:
    artifact: ProjectReference
    timeline_revision_sha256: str
    video_track_id: str
    audio_track_id: str | None
    duration_us: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": self.artifact.to_dict(),
            "timeline_revision_sha256": self.timeline_revision_sha256,
            "video_track_id": self.video_track_id,
            "audio_track_id": self.audio_track_id,
            "duration_us": self.duration_us,
        }


class StudioTimelineRenderService:
    """Render a bounded Studio timeline using the proven local FFmpeg runtime."""

    def __init__(self, project_store: ProjectStore, ffmpeg: LocalFFmpegAdapter) -> None:
        self.project_store = project_store
        self.timelines = TimelineStore(project_store)
        self.ffmpeg = ffmpeg

    @staticmethod
    def _active_clips(track: TimelineTrack) -> tuple[TimelineClip, ...]:
        if not track.enabled:
            return ()
        if track.kind == "audio" and track.muted:
            return ()
        return tuple(
            clip
            for clip in track.clips
            if clip.enabled and not (track.kind == "audio" and clip.muted)
        )

    @staticmethod
    def _require_contiguous(clips: tuple[TimelineClip, ...]) -> int:
        cursor = 0
        for clip in clips:
            if clip.timeline_start_us != cursor:
                raise StudioRenderError(
                    "first Studio renderer requires a contiguous visual track without gaps"
                )
            cursor = clip.timeline_end_us
        return cursor

    def render(self, project_id: str) -> StudioRenderResult:
        try:
            timeline = self.timelines.load(project_id, validate_references=True)
            projection = StudioMLTTimelineAdapter(self.project_store).project(project_id)
        except (TimelineError, StudioMLTError, ProjectStoreError) as exc:
            raise StudioRenderError(str(exc)) from exc

        visual_tracks = [
            track
            for track in timeline.tracks
            if track.kind == "video" and self._active_clips(track)
        ]
        if len(visual_tracks) != 1:
            raise StudioRenderError(
                "first Studio renderer requires exactly one active visual track"
            )
        video_track = visual_tracks[0]
        visual_clips = self._active_clips(video_track)
        if not visual_clips:
            raise StudioRenderError("Studio timeline has no renderable visual clips")
        expected_duration_us = self._require_contiguous(visual_clips)

        audio_tracks = [
            track
            for track in timeline.tracks
            if track.kind == "audio" and self._active_clips(track)
        ]
        if len(audio_tracks) > 1:
            raise StudioRenderError(
                "first Studio renderer supports at most one active audio track"
            )
        audio_track = audio_tracks[0] if audio_tracks else None
        audio_clip: TimelineClip | None = None
        if audio_track is not None:
            active_audio = self._active_clips(audio_track)
            if len(active_audio) != 1:
                raise StudioRenderError(
                    "first Studio renderer supports one active audio clip"
                )
            audio_clip = active_audio[0]
            if audio_clip.timeline_start_us != 0:
                raise StudioRenderError(
                    "first Studio renderer requires the audio clip to start at timeline zero"
                )
            if audio_clip.duration_us < expected_duration_us:
                raise StudioRenderError(
                    "first Studio renderer requires audio to cover the full visual duration"
                )

        artifact_id = f"art_{uuid.uuid4().hex}"
        canonical_output = f"exports/{artifact_id}.mp4"
        try:
            output_path = self.project_store.resolve_project_file(
                project_id,
                canonical_output,
                must_exist=False,
                allowed_roots=("exports",),
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise StudioRenderError(str(exc)) from exc
        if output_path.exists() or output_path.is_symlink():
            raise StudioRenderError("Studio export refuses to overwrite an existing file")

        tasks_dir = self.project_store.project_directory(project_id) / "tasks"
        segment_paths: list[Path] = []
        manifest_path: Path | None = None
        visual_master: Path | None = None
        revision = _revision_sha256(timeline.to_dict())
        try:
            for clip in visual_clips:
                reference_info = self.timelines.reference(project_id, clip.reference_id)
                reference = reference_info.reference
                source = reference_info.path
                segment_path = tasks_dir / f"studio-segment-{uuid.uuid4().hex}.mp4"
                segment_paths.append(segment_path)
                common_tail = [
                    "-vf",
                    _video_filter(
                        projection.width,
                        projection.height,
                        projection.frame_rate_num,
                        projection.frame_rate_den,
                    ),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(segment_path),
                ]
                if reference.kind == "image":
                    command = [
                        self.ffmpeg._tool("ffmpeg"),
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-n",
                        "-loop",
                        "1",
                        "-i",
                        str(source),
                        "-t",
                        f"{clip.duration_us}us",
                        *common_tail,
                    ]
                elif reference.kind == "video":
                    command = [
                        self.ffmpeg._tool("ffmpeg"),
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-n",
                        "-i",
                        str(source),
                        "-ss",
                        f"{clip.source_start_us}us",
                        "-t",
                        f"{clip.duration_us}us",
                        "-map",
                        "0:v:0",
                        *common_tail,
                    ]
                else:  # TimelineStore already guards this invariant.
                    raise StudioRenderError(
                        f"visual track contains unsupported media kind {reference.kind!r}"
                    )
                self.ffmpeg._invoke(
                    command,
                    timeout=self.ffmpeg.assemble_timeout_sec,
                    tool="ffmpeg",
                )
                if not segment_path.is_file() or segment_path.stat().st_size <= 0:
                    raise CapabilityToolFailed("Studio normalized visual segment was not created")

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix="studio-render-",
                suffix=".ffconcat",
                dir=tasks_dir,
                delete=False,
            ) as handle:
                manifest_path = Path(handle.name)
                handle.write("ffconcat version 1.0\n")
                for segment_path in segment_paths:
                    handle.write(_concat_quote(segment_path))

            visual_output = output_path
            if audio_clip is not None:
                visual_master = tasks_dir / f"studio-visual-{uuid.uuid4().hex}.mp4"
                visual_output = visual_master

            self.ffmpeg._invoke(
                [
                    self.ffmpeg._tool("ffmpeg"),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-n",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(manifest_path),
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(visual_output),
                ],
                timeout=self.ffmpeg.assemble_timeout_sec,
                tool="ffmpeg",
            )
            if not visual_output.is_file() or visual_output.stat().st_size <= 0:
                raise CapabilityToolFailed("Studio visual master was not created")

            if audio_clip is not None and audio_track is not None:
                audio_info = self.timelines.reference(project_id, audio_clip.reference_id)
                self.ffmpeg._invoke(
                    [
                        self.ffmpeg._tool("ffmpeg"),
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-n",
                        "-i",
                        str(visual_output),
                        "-ss",
                        f"{audio_clip.source_start_us}us",
                        "-i",
                        str(audio_info.path),
                        "-t",
                        f"{expected_duration_us}us",
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-movflags",
                        "+faststart",
                        str(output_path),
                    ],
                    timeout=self.ffmpeg.assemble_timeout_sec,
                    tool="ffmpeg",
                )

            if not output_path.is_file() or output_path.is_symlink() or output_path.stat().st_size <= 0:
                raise CapabilityToolFailed("Studio export is not a non-empty regular file")
            output_probe = self.ffmpeg._probe_path(
                canonical_path=canonical_output,
                source=output_path,
            )
            actual_duration_us = output_probe.get("duration_us")
            if (
                output_probe.get("has_video") is not True
                or not isinstance(actual_duration_us, int)
                or actual_duration_us <= 0
            ):
                raise CapabilityToolFailed("Studio export is not a valid video")
            if (audio_clip is not None) != (output_probe.get("has_audio") is True):
                raise CapabilityToolFailed("Studio export audio presence does not match timeline")
            if abs(actual_duration_us - expected_duration_us) > _DURATION_TOLERANCE_US:
                raise CapabilityToolFailed("Studio export duration does not match canonical timeline")

            artifact = ProjectReference(
                id=artifact_id,
                kind="video",
                path=canonical_output,
                metadata={
                    "role": "studio-export",
                    "lifecycle": "final",
                    "composition_mode": "studio_v2_contiguous_visual_track",
                    "timeline_id": timeline.timeline_id,
                    "timeline_revision_sha256": revision,
                    "video_track_id": video_track.track_id,
                    "audio_track_id": audio_track.track_id if audio_track is not None else None,
                    "clip_ids": [clip.clip_id for clip in visual_clips],
                    "expected_duration_us": expected_duration_us,
                    "actual_duration_us": actual_duration_us,
                    "width": projection.width,
                    "height": projection.height,
                    "frame_rate": f"{projection.frame_rate_num}/{projection.frame_rate_den}",
                    "content_type": "video/mp4",
                },
            )
            project = self.project_store.load_project(project_id)
            self.project_store.update_project(
                project_id,
                artifacts=(*project.artifacts, artifact),
            )
            return StudioRenderResult(
                artifact=artifact,
                timeline_revision_sha256=revision,
                video_track_id=video_track.track_id,
                audio_track_id=audio_track.track_id if audio_track is not None else None,
                duration_us=actual_duration_us,
            )
        except Exception:
            output_path.unlink(missing_ok=True)
            raise
        finally:
            if manifest_path is not None:
                manifest_path.unlink(missing_ok=True)
            for segment_path in segment_paths:
                segment_path.unlink(missing_ok=True)
            if visual_master is not None:
                visual_master.unlink(missing_ok=True)
