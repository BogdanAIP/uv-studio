"""Deterministic existing-video range reinsertion for the local FFmpeg adapter.

This module deliberately extends the existing local adapter instead of exposing raw
FFmpeg/filtergraph inputs. The first contract is narrow and fail-closed: one video
stream, at most one audio stream, matching source/replacement geometry and no
implicit replacement retiming.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from uv_studio.projects.media_ranges import ProjectMediaRange
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectStoreError

from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import CapabilityOffer
from .local_ffmpeg import LocalFFmpegAdapter as BaseLocalFFmpegAdapter
from .local_ffmpeg import _parse_duration_us

_REPLACE_OFFER_ID = "local_ffmpeg.video_replace_range"
_REPLACE_OUTPUT_ROOTS = ("artifacts",)
_REPLACEMENT_DURATION_TOLERANCE_US = 100_000
_FINAL_VIDEO_DURATION_TOLERANCE_US = 250_000
_SOURCE_AV_DURATION_TOLERANCE_US = 250_000
_COMPOSITION_MODE = "filter_concat_ffv1_flac_vfr"
_AUDIO_POLICY = "matching_presence_single_track"
_VIDEO_MATCH_FIELDS = (
    "pix_fmt",
    "sample_aspect_ratio",
    "color_range",
    "color_space",
    "color_transfer",
    "color_primaries",
)
_AUDIO_MATCH_FIELDS = (
    "sample_fmt",
    "sample_rate",
    "channels",
    "channel_layout",
)


def _stream_count(probe: Mapping[str, Any], kind: str) -> int:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        return 0
    return sum(
        1
        for item in streams
        if isinstance(item, Mapping) and item.get("codec_type") == kind
    )


def _primary_stream(probe: Mapping[str, Any], kind: str) -> Mapping[str, Any] | None:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        return None
    for item in streams:
        if isinstance(item, Mapping) and item.get("codec_type") == kind:
            return item
    return None


def _unsupported_stream_types(probe: Mapping[str, Any]) -> set[str]:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        return set()
    return {
        str(item.get("codec_type"))
        for item in streams
        if isinstance(item, Mapping)
        and item.get("codec_type") not in {"video", "audio"}
    }


def _video_duration_us(probe: Mapping[str, Any]) -> int | None:
    video = probe.get("video")
    if isinstance(video, Mapping):
        value = video.get("duration_us")
        if isinstance(value, int) and value > 0:
            return value
    value = probe.get("duration_us")
    if isinstance(value, int) and value > 0:
        return value
    return None


def _audio_duration_us(probe: Mapping[str, Any]) -> int | None:
    stream = _primary_stream(probe, "audio")
    if stream is not None:
        parsed = _parse_duration_us(stream.get("duration"))
        if isinstance(parsed, int) and parsed > 0:
            return parsed
    value = probe.get("duration_us")
    if isinstance(value, int) and value > 0:
        return value
    return None


def _video_geometry(probe: Mapping[str, Any]) -> tuple[int, int] | None:
    video = probe.get("video")
    if not isinstance(video, Mapping):
        return None
    width = video.get("width")
    height = video.get("height")
    if (
        isinstance(width, int)
        and not isinstance(width, bool)
        and width > 0
        and isinstance(height, int)
        and not isinstance(height, bool)
        and height > 0
    ):
        return width, height
    return None


def _require_matching_known_fields(
    source_probe: Mapping[str, Any],
    replacement_probe: Mapping[str, Any],
    *,
    kind: str,
    fields: tuple[str, ...],
) -> None:
    source_stream = _primary_stream(source_probe, kind)
    replacement_stream = _primary_stream(replacement_probe, kind)
    if source_stream is None or replacement_stream is None:
        return
    mismatched: list[str] = []
    for field in fields:
        source_value = source_stream.get(field)
        replacement_value = replacement_stream.get(field)
        if (
            source_value not in (None, "", "unknown", "N/A")
            and replacement_value not in (None, "", "unknown", "N/A")
            and str(source_value) != str(replacement_value)
        ):
            mismatched.append(field)
    if mismatched:
        raise InvalidCapabilityInput(
            f"video.replace_range requires matching known {kind} parameters: {mismatched!r}"
        )


def _trim_video(input_index: int, start_us: int | None, end_us: int | None, label: str) -> str:
    # ProjectMediaRange is zero-based media time. Normalize the decoded input before
    # applying trim so non-zero source PTS/start offsets cannot shift the requested range.
    base = f"[{input_index}:v:0]setpts=PTS-STARTPTS"
    options: list[str] = []
    if start_us is not None:
        options.append(f"start={start_us}us")
    if end_us is not None:
        options.append(f"end={end_us}us")
    if not options:
        return f"{base}[{label}]"
    trim = "trim=" + ":".join(options)
    return f"{base},{trim},setpts=PTS-STARTPTS[{label}]"


def _trim_audio(input_index: int, start_us: int | None, end_us: int | None, label: str) -> str:
    base = f"[{input_index}:a:0]asetpts=PTS-STARTPTS"
    options: list[str] = []
    if start_us is not None:
        options.append(f"start={start_us}us")
    if end_us is not None:
        options.append(f"end={end_us}us")
    if not options:
        return f"{base}[{label}]"
    trim = "atrim=" + ":".join(options)
    return f"{base},{trim},asetpts=PTS-STARTPTS[{label}]"


def _build_filter_graph(
    *,
    start_us: int,
    end_us: int,
    source_duration_us: int,
    has_audio: bool,
) -> str:
    parts: list[str] = []
    segment_labels: list[tuple[str, str | None]] = []
    segment_index = 0

    if start_us > 0:
        vlabel = f"v{segment_index}"
        parts.append(_trim_video(0, 0, start_us, vlabel))
        alabel = None
        if has_audio:
            alabel = f"a{segment_index}"
            parts.append(_trim_audio(0, 0, start_us, alabel))
        segment_labels.append((vlabel, alabel))
        segment_index += 1

    vlabel = f"v{segment_index}"
    parts.append(_trim_video(1, None, None, vlabel))
    alabel = None
    if has_audio:
        alabel = f"a{segment_index}"
        parts.append(_trim_audio(1, None, None, alabel))
    segment_labels.append((vlabel, alabel))
    segment_index += 1

    if end_us < source_duration_us:
        vlabel = f"v{segment_index}"
        parts.append(_trim_video(0, end_us, source_duration_us, vlabel))
        alabel = None
        if has_audio:
            alabel = f"a{segment_index}"
            parts.append(_trim_audio(0, end_us, source_duration_us, alabel))
        segment_labels.append((vlabel, alabel))

    if len(segment_labels) == 1:
        only_v, only_a = segment_labels[0]
        parts.append(f"[{only_v}]null[vout]")
        if has_audio and only_a is not None:
            parts.append(f"[{only_a}]anull[aout]")
        return ";".join(parts)

    if has_audio:
        concat_inputs = "".join(
            f"[{video_label}][{audio_label}]"
            for video_label, audio_label in segment_labels
            if audio_label is not None
        )
        parts.append(
            f"{concat_inputs}concat=n={len(segment_labels)}:v=1:a=1[vout][aout]"
        )
    else:
        concat_inputs = "".join(f"[{video_label}]" for video_label, _ in segment_labels)
        parts.append(f"{concat_inputs}concat=n={len(segment_labels)}:v=1:a=0[vout]")
    return ";".join(parts)


class LocalFFmpegRangeAdapter(BaseLocalFFmpegAdapter):
    """Package-level local FFmpeg adapter with deterministic range reinsertion."""

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        if offer.capability_id != "video.replace_range":
            return super().execute(project_id=project_id, offer=offer, payload=payload)
        self._validate_offer(offer)
        if offer.offer_id != _REPLACE_OFFER_ID:
            raise UnsupportedCapabilityExecution(
                f"range reinsertion requires exact offer {_REPLACE_OFFER_ID!r}"
            )
        if not isinstance(payload, Mapping):
            raise InvalidCapabilityInput("capability input must be a JSON object")
        return self._replace_range(project_id=project_id, offer=offer, payload=payload)

    def _replace_range(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        allowed = {"source_path", "replacement_path", "start_us", "end_us"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(
                f"unsupported video.replace_range fields: {sorted(unknown)!r}"
            )
        source_path = payload.get("source_path")
        replacement_path = payload.get("replacement_path")
        if not isinstance(source_path, str):
            raise InvalidCapabilityInput("video.replace_range requires string field 'source_path'")
        if not isinstance(replacement_path, str):
            raise InvalidCapabilityInput(
                "video.replace_range requires string field 'replacement_path'"
            )
        try:
            requested = ProjectMediaRange(
                source_path=source_path,
                start_us=payload.get("start_us"),
                end_us=payload.get("end_us"),
            )
        except ProjectValidationError as exc:
            raise InvalidCapabilityInput(str(exc)) from exc

        canonical_source, source = self._resolve_input_file(
            project_id,
            requested.source_path,
            operation="video.replace_range source",
        )
        canonical_replacement, replacement = self._resolve_input_file(
            project_id,
            replacement_path,
            operation="video.replace_range replacement",
        )
        source_probe = self._probe_path(canonical_path=canonical_source, source=source)
        replacement_probe = self._probe_path(
            canonical_path=canonical_replacement,
            source=replacement,
        )

        if _stream_count(source_probe, "video") != 1:
            raise InvalidCapabilityInput(
                "video.replace_range currently requires exactly one source video stream"
            )
        if _stream_count(replacement_probe, "video") != 1:
            raise InvalidCapabilityInput(
                "video.replace_range currently requires exactly one replacement video stream"
            )
        source_unsupported = _unsupported_stream_types(source_probe)
        replacement_unsupported = _unsupported_stream_types(replacement_probe)
        if source_unsupported:
            raise InvalidCapabilityInput(
                "video.replace_range source contains unsupported stream types: "
                f"{sorted(source_unsupported)!r}"
            )
        if replacement_unsupported:
            raise InvalidCapabilityInput(
                "video.replace_range replacement contains unsupported stream types: "
                f"{sorted(replacement_unsupported)!r}"
            )

        source_audio_count = _stream_count(source_probe, "audio")
        replacement_audio_count = _stream_count(replacement_probe, "audio")
        if source_audio_count > 1 or replacement_audio_count > 1:
            raise InvalidCapabilityInput(
                "video.replace_range currently supports at most one audio stream per input"
            )
        if source_audio_count != replacement_audio_count:
            raise InvalidCapabilityInput(
                "video.replace_range requires matching source/replacement audio presence"
            )
        has_audio = source_audio_count == 1

        source_geometry = _video_geometry(source_probe)
        replacement_geometry = _video_geometry(replacement_probe)
        if source_geometry is None or replacement_geometry is None:
            raise InvalidCapabilityInput(
                "video.replace_range requires known positive source/replacement dimensions"
            )
        if source_geometry != replacement_geometry:
            raise InvalidCapabilityInput(
                "video.replace_range requires replacement resolution to match the source"
            )
        _require_matching_known_fields(
            source_probe,
            replacement_probe,
            kind="video",
            fields=_VIDEO_MATCH_FIELDS,
        )
        if has_audio:
            _require_matching_known_fields(
                source_probe,
                replacement_probe,
                kind="audio",
                fields=_AUDIO_MATCH_FIELDS,
            )

        source_duration_us = _video_duration_us(source_probe)
        replacement_duration_us = _video_duration_us(replacement_probe)
        if source_duration_us is None:
            raise InvalidCapabilityInput(
                "video.replace_range requires a known positive source video duration"
            )
        if replacement_duration_us is None:
            raise InvalidCapabilityInput(
                "video.replace_range requires a known positive replacement video duration"
            )
        try:
            resolved_range = requested.resolve(source_duration_us)
        except ProjectValidationError as exc:
            raise InvalidCapabilityInput(str(exc)) from exc

        replacement_delta_us = replacement_duration_us - requested.duration_us
        if abs(replacement_delta_us) > _REPLACEMENT_DURATION_TOLERANCE_US:
            raise InvalidCapabilityInput(
                "replacement video duration differs from the requested range by more than "
                f"{_REPLACEMENT_DURATION_TOLERANCE_US} microseconds"
            )
        source_audio_duration_us: int | None = None
        replacement_audio_duration_us: int | None = None
        if has_audio:
            source_audio_duration_us = _audio_duration_us(source_probe)
            replacement_audio_duration_us = _audio_duration_us(replacement_probe)
            if source_audio_duration_us is None:
                raise InvalidCapabilityInput(
                    "video.replace_range requires a known positive source audio duration"
                )
            if replacement_audio_duration_us is None:
                raise InvalidCapabilityInput(
                    "video.replace_range requires a known positive replacement audio duration"
                )
            if (
                abs(source_audio_duration_us - source_duration_us)
                > _SOURCE_AV_DURATION_TOLERANCE_US
            ):
                raise InvalidCapabilityInput(
                    "source audio/video durations differ beyond the supported reinsertion tolerance"
                )
            if (
                abs(replacement_audio_duration_us - replacement_duration_us)
                > _REPLACEMENT_DURATION_TOLERANCE_US
            ):
                raise InvalidCapabilityInput(
                    "replacement audio/video durations differ beyond the supported tolerance"
                )

        artifact_id = f"art_{uuid.uuid4().hex}"
        canonical_output = f"artifacts/{artifact_id}.mkv"
        try:
            output_path = self.store.resolve_project_file(
                project_id,
                canonical_output,
                must_exist=False,
                allowed_roots=_REPLACE_OUTPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        if output_path.exists() or output_path.is_symlink():
            raise InvalidCapabilityInput(
                f"video.replace_range refuses to overwrite existing output: {canonical_output!r}"
            )

        filter_graph = _build_filter_graph(
            start_us=resolved_range.start_us,
            end_us=resolved_range.end_us,
            source_duration_us=source_duration_us,
            has_audio=has_audio,
        )
        command = [
            self._tool("ffmpeg"),
            "-hide_banner",
            "-loglevel",
            "error",
            "-n",
            "-i",
            str(source),
            "-i",
            str(replacement),
            "-filter_complex",
            filter_graph,
            "-map",
            "[vout]",
        ]
        if has_audio:
            command.extend(["-map", "[aout]"])
        command.extend(
            [
                "-fps_mode",
                "passthrough",
                "-c:v",
                "ffv1",
                "-level",
                "3",
            ]
        )
        if has_audio:
            command.extend(["-c:a", "flac"])
        command.append(str(output_path))

        expected_output_duration_us = (
            source_duration_us - requested.duration_us + replacement_duration_us
        )
        try:
            self._invoke(command, timeout=self.extract_timeout_sec, tool="ffmpeg")
            try:
                validated_output = self.store.resolve_project_file(
                    project_id,
                    canonical_output,
                    must_exist=True,
                    allowed_roots=_REPLACE_OUTPUT_ROOTS,
                )
            except (ProjectValidationError, ProjectStoreError) as exc:
                raise CapabilityToolFailed(
                    "ffmpeg replacement output escaped its project artifact boundary"
                ) from exc
            if validated_output != output_path or output_path.is_symlink():
                raise CapabilityToolFailed(
                    "ffmpeg replacement output must be a regular UV Studio-owned artifact file"
                )
            try:
                output_size = validated_output.stat().st_size if validated_output.is_file() else 0
            except OSError as exc:
                raise CapabilityToolFailed(
                    "ffmpeg replacement output could not be validated"
                ) from exc
            if output_size <= 0:
                raise CapabilityToolFailed(
                    "ffmpeg reported success but replacement output is empty or missing"
                )

            output_probe = self._probe_path(
                canonical_path=canonical_output,
                source=validated_output,
            )
            if _stream_count(output_probe, "video") != 1:
                raise CapabilityToolFailed(
                    "ffmpeg replacement output is not a single-video-stream clip"
                )
            if _stream_count(output_probe, "audio") != source_audio_count:
                raise CapabilityToolFailed(
                    "ffmpeg replacement output audio presence does not match the declared policy"
                )
            if _video_geometry(output_probe) != source_geometry:
                raise CapabilityToolFailed(
                    "ffmpeg replacement output geometry changed unexpectedly"
                )
            actual_output_duration_us = _video_duration_us(output_probe)
            if actual_output_duration_us is None:
                raise CapabilityToolFailed(
                    "ffmpeg replacement output has no known positive video duration"
                )
            output_duration_delta_us = actual_output_duration_us - expected_output_duration_us
            if abs(output_duration_delta_us) > _FINAL_VIDEO_DURATION_TOLERANCE_US:
                raise CapabilityToolFailed(
                    "ffmpeg replacement output duration is inconsistent with reinsertion policy"
                )

            artifact = ProjectReference(
                id=artifact_id,
                kind="video",
                path=canonical_output,
                metadata={
                    "capability_id": offer.capability_id,
                    "offer_id": offer.offer_id,
                    "source_path": canonical_source,
                    "replacement_path": canonical_replacement,
                    "requested_range": requested.to_dict(),
                    "source_video_duration_us": source_duration_us,
                    "source_audio_duration_us": source_audio_duration_us,
                    "replacement_video_duration_us": replacement_duration_us,
                    "replacement_audio_duration_us": replacement_audio_duration_us,
                    "replacement_duration_delta_us": replacement_delta_us,
                    "expected_output_video_duration_us": expected_output_duration_us,
                    "actual_output_video_duration_us": actual_output_duration_us,
                    "output_duration_delta_us": output_duration_delta_us,
                    "composition_mode": _COMPOSITION_MODE,
                    "audio_policy": _AUDIO_POLICY,
                    "replacement_duration_tolerance_us": _REPLACEMENT_DURATION_TOLERANCE_US,
                    "source_av_duration_tolerance_us": _SOURCE_AV_DURATION_TOLERANCE_US,
                    "final_duration_tolerance_us": _FINAL_VIDEO_DURATION_TOLERANCE_US,
                    "lifecycle": "intermediate",
                },
            )
            project = self.store.load_project(project_id)
            self.store.update_project(
                project_id,
                artifacts=(*project.artifacts, artifact),
            )
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "path": canonical_output,
                "source_path": canonical_source,
                "replacement_path": canonical_replacement,
                "range": resolved_range.to_dict(),
                "replacement_duration_delta_us": replacement_delta_us,
                "expected_output_video_duration_us": expected_output_duration_us,
                "actual_output_video_duration_us": actual_output_duration_us,
                "composition_mode": _COMPOSITION_MODE,
                "audio_policy": _AUDIO_POLICY,
            },
            artifact=artifact.to_dict(),
        )
