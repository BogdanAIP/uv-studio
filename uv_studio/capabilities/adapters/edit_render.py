"""Explicit one-pass render projection for canonical non-destructive range edits."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from uv_studio.projects import EditStateError, RangeEditStateStore
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectStoreError

from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import (
    CapabilityDefinition,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from ..registry import CapabilityRegistry
from .range_reinsertion import (
    _AUDIO_MATCH_FIELDS,
    _AV_START_ALIGNMENT_TOLERANCE_US,
    _FINAL_VIDEO_DURATION_TOLERANCE_US,
    _REPLACEMENT_DURATION_TOLERANCE_US,
    _SOURCE_AV_DURATION_TOLERANCE_US,
    _VIDEO_MATCH_FIELDS,
    _audio_duration_us,
    _primary_stream,
    _require_matching_known_fields,
    _stream_count,
    _stream_start_us,
    _trim_audio,
    _trim_video,
    _unsupported_stream_types,
    _video_duration_us,
    _video_geometry,
)

if TYPE_CHECKING:
    from .range_reinsertion import LocalFFmpegRangeAdapter

_EDIT_RENDER_CAPABILITY_ID = "video.render_edits"
_EDIT_RENDER_OFFER_ID = "local_ffmpeg.video_render_edits"
_EDIT_RENDER_OUTPUT_ROOTS = ("artifacts",)
_COMPOSITION_MODE = "edit_state_filter_concat_ffv1_flac_vfr"
_AUDIO_POLICY = "matching_presence_single_track"


def register_edit_render_capability(registry: CapabilityRegistry) -> None:
    """Register the explicit render projection without turning edit acceptance into execution."""
    registry.register_capability(
        CapabilityDefinition(
            _EDIT_RENDER_CAPABILITY_ID,
            "Рендер принятых правок",
            (
                "Явная детерминированная материализация принятого non-destructive edit state "
                "в один проектный видеоартефакт."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.VIDEO, MediaKind.TIMELINE),
            (MediaKind.VIDEO,),
            asynchronous=False,
        )
    )
    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    registry.register_offer(
        CapabilityOffer(
            offer_id=_EDIT_RENDER_OFFER_ID,
            capability_id=_EDIT_RENDER_CAPABILITY_ID,
            adapter_id="local_ffmpeg",
            title="FFmpeg one-pass accepted edit-state render",
            availability=(
                OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE
            ),
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; явный локальный render edit state доступен."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=("video.edit_state", "video.render", "video.lossless_intermediate"),
        )
    )


def _build_filter_graph(*, edits, source_duration_us: int, has_audio: bool) -> str:
    parts: list[str] = []
    segment_labels: list[tuple[str, str | None]] = []
    cursor_us = 0
    segment_index = 0

    def source_segment(start_us: int, end_us: int) -> None:
        nonlocal segment_index
        if end_us <= start_us:
            return
        video_label = f"v{segment_index}"
        parts.append(_trim_video(0, start_us, end_us, video_label))
        audio_label = None
        if has_audio:
            audio_label = f"a{segment_index}"
            parts.append(_trim_audio(0, start_us, end_us, audio_label))
        segment_labels.append((video_label, audio_label))
        segment_index += 1

    def replacement_segment(input_index: int) -> None:
        nonlocal segment_index
        video_label = f"v{segment_index}"
        parts.append(_trim_video(input_index, None, None, video_label))
        audio_label = None
        if has_audio:
            audio_label = f"a{segment_index}"
            parts.append(_trim_audio(input_index, None, None, audio_label))
        segment_labels.append((video_label, audio_label))
        segment_index += 1

    for replacement_index, edit in enumerate(edits, start=1):
        source_segment(cursor_us, edit.start_us)
        replacement_segment(replacement_index)
        cursor_us = edit.end_us
    source_segment(cursor_us, source_duration_us)

    if not segment_labels:
        raise InvalidCapabilityInput("video.render_edits produced no renderable timeline segments")
    if len(segment_labels) == 1:
        video_label, audio_label = segment_labels[0]
        parts.append(f"[{video_label}]null[vout]")
        if has_audio and audio_label is not None:
            parts.append(f"[{audio_label}]anull[aout]")
        return ";".join(parts)

    if has_audio:
        inputs = "".join(
            f"[{video_label}][{audio_label}]"
            for video_label, audio_label in segment_labels
            if audio_label is not None
        )
        parts.append(f"{inputs}concat=n={len(segment_labels)}:v=1:a=1[vout][aout]")
    else:
        inputs = "".join(f"[{video_label}]" for video_label, _ in segment_labels)
        parts.append(f"{inputs}concat=n={len(segment_labels)}:v=1:a=0[vout]")
    return ";".join(parts)


def render_edit_state(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _EDIT_RENDER_OFFER_ID:
        raise UnsupportedCapabilityExecution(
            f"edit-state render requires exact offer {_EDIT_RENDER_OFFER_ID!r}"
        )
    allowed = {"source_path"}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported video.render_edits fields: {sorted(unknown)!r}"
        )
    source_path = payload.get("source_path")
    if not isinstance(source_path, str):
        raise InvalidCapabilityInput("video.render_edits requires string field 'source_path'")

    try:
        state = RangeEditStateStore(adapter.store).load(project_id)
    except EditStateError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    try:
        edits = state.for_source(source_path)
    except ProjectValidationError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    if not edits:
        raise InvalidCapabilityInput("video.render_edits requires at least one accepted edit for source_path")

    canonical_source, source = adapter._resolve_input_file(
        project_id,
        source_path,
        operation="video.render_edits source",
    )
    source_probe = adapter._probe_path(canonical_path=canonical_source, source=source)
    if _stream_count(source_probe, "video") != 1:
        raise InvalidCapabilityInput(
            "video.render_edits currently requires exactly one source video stream"
        )
    unsupported = _unsupported_stream_types(source_probe)
    if unsupported:
        raise InvalidCapabilityInput(
            "video.render_edits source contains unsupported stream types: "
            f"{sorted(unsupported)!r}"
        )
    source_audio_count = _stream_count(source_probe, "audio")
    if source_audio_count > 1:
        raise InvalidCapabilityInput(
            "video.render_edits currently supports at most one source audio stream"
        )
    has_audio = source_audio_count == 1
    source_geometry = _video_geometry(source_probe)
    if source_geometry is None:
        raise InvalidCapabilityInput(
            "video.render_edits requires known positive source dimensions"
        )
    source_duration_us = _video_duration_us(source_probe)
    if source_duration_us is None:
        raise InvalidCapabilityInput(
            "video.render_edits requires a known positive source video duration"
        )

    source_audio_duration_us: int | None = None
    if has_audio:
        source_audio_duration_us = _audio_duration_us(source_probe)
        if source_audio_duration_us is None:
            raise InvalidCapabilityInput(
                "video.render_edits requires a known positive source audio duration"
            )
        if abs(source_audio_duration_us - source_duration_us) > _SOURCE_AV_DURATION_TOLERANCE_US:
            raise InvalidCapabilityInput(
                "source audio/video durations differ beyond the supported render tolerance"
            )
        video_start = _stream_start_us(source_probe, "video")
        audio_start = _stream_start_us(source_probe, "audio")
        if video_start is None or audio_start is None:
            raise InvalidCapabilityInput(
                "video.render_edits requires known source video/audio start_time values"
            )
        if abs(audio_start - video_start) > _AV_START_ALIGNMENT_TOLERANCE_US:
            raise InvalidCapabilityInput(
                "source audio/video start timestamps are not aligned closely enough"
            )

    replacement_paths = []
    replacement_durations_us: list[int] = []
    for edit in edits:
        try:
            edit_range = edit.to_dict()
            # Resolve against the probed source now; acceptance intentionally performs no media I/O.
            from uv_studio.projects.media_ranges import ProjectMediaRange

            ProjectMediaRange(
                source_path=edit.source_path,
                start_us=edit.start_us,
                end_us=edit.end_us,
            ).resolve(source_duration_us)
        except ProjectValidationError as exc:
            raise InvalidCapabilityInput(
                f"accepted edit {edit.edit_id!r} is outside the current source duration: {exc}"
            ) from exc
        canonical_replacement, replacement = adapter._resolve_input_file(
            project_id,
            edit.replacement_path,
            operation=f"video.render_edits replacement {edit.edit_id}",
        )
        replacement_probe = adapter._probe_path(
            canonical_path=canonical_replacement,
            source=replacement,
        )
        if _stream_count(replacement_probe, "video") != 1:
            raise InvalidCapabilityInput(
                f"accepted edit {edit.edit_id!r} replacement must contain exactly one video stream"
            )
        replacement_unsupported = _unsupported_stream_types(replacement_probe)
        if replacement_unsupported:
            raise InvalidCapabilityInput(
                f"accepted edit {edit.edit_id!r} replacement contains unsupported stream types: "
                f"{sorted(replacement_unsupported)!r}"
            )
        replacement_audio_count = _stream_count(replacement_probe, "audio")
        if replacement_audio_count > 1 or replacement_audio_count != source_audio_count:
            raise InvalidCapabilityInput(
                f"accepted edit {edit.edit_id!r} replacement audio presence must match the source"
            )
        if _video_geometry(replacement_probe) != source_geometry:
            raise InvalidCapabilityInput(
                f"accepted edit {edit.edit_id!r} replacement resolution must match the source"
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
        replacement_duration_us = _video_duration_us(replacement_probe)
        if replacement_duration_us is None:
            raise InvalidCapabilityInput(
                f"accepted edit {edit.edit_id!r} replacement has no known positive video duration"
            )
        if abs(replacement_duration_us - edit.duration_us) > _REPLACEMENT_DURATION_TOLERANCE_US:
            raise InvalidCapabilityInput(
                f"accepted edit {edit.edit_id!r} replacement duration differs from its range by "
                f"more than {_REPLACEMENT_DURATION_TOLERANCE_US} microseconds"
            )
        if has_audio:
            replacement_audio_duration_us = _audio_duration_us(replacement_probe)
            if replacement_audio_duration_us is None:
                raise InvalidCapabilityInput(
                    f"accepted edit {edit.edit_id!r} replacement has no known positive audio duration"
                )
            if abs(replacement_audio_duration_us - replacement_duration_us) > _REPLACEMENT_DURATION_TOLERANCE_US:
                raise InvalidCapabilityInput(
                    f"accepted edit {edit.edit_id!r} replacement audio/video durations differ beyond tolerance"
                )
            video_start = _stream_start_us(replacement_probe, "video")
            audio_start = _stream_start_us(replacement_probe, "audio")
            if video_start is None or audio_start is None:
                raise InvalidCapabilityInput(
                    f"accepted edit {edit.edit_id!r} replacement requires known AV start timestamps"
                )
            if abs(audio_start - video_start) > _AV_START_ALIGNMENT_TOLERANCE_US:
                raise InvalidCapabilityInput(
                    f"accepted edit {edit.edit_id!r} replacement AV start timestamps are not aligned"
                )
        replacement_paths.append((canonical_replacement, replacement))
        replacement_durations_us.append(replacement_duration_us)

    artifact_id = f"art_{uuid.uuid4().hex}"
    canonical_output = f"artifacts/{artifact_id}.mkv"
    try:
        output_path = adapter.store.resolve_project_file(
            project_id,
            canonical_output,
            must_exist=False,
            allowed_roots=_EDIT_RENDER_OUTPUT_ROOTS,
        )
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    if output_path.exists() or output_path.is_symlink():
        raise InvalidCapabilityInput(
            f"video.render_edits refuses to overwrite existing output: {canonical_output!r}"
        )

    filter_graph = _build_filter_graph(
        edits=edits,
        source_duration_us=source_duration_us,
        has_audio=has_audio,
    )
    command = [
        adapter._tool("ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-i",
        str(source),
    ]
    for _, replacement in replacement_paths:
        command.extend(["-i", str(replacement)])
    command.extend(["-filter_complex", filter_graph, "-map", "[vout]"])
    if has_audio:
        command.extend(["-map", "[aout]"])
    command.extend(["-fps_mode", "passthrough", "-c:v", "ffv1", "-level", "3"])
    if has_audio:
        command.extend(["-c:a", "flac"])
    command.append(str(output_path))

    expected_duration_us = source_duration_us + sum(
        replacement_duration - edit.duration_us
        for replacement_duration, edit in zip(replacement_durations_us, edits)
    )
    try:
        adapter._invoke(command, timeout=adapter.extract_timeout_sec, tool="ffmpeg")
        try:
            validated_output = adapter.store.resolve_project_file(
                project_id,
                canonical_output,
                must_exist=True,
                allowed_roots=_EDIT_RENDER_OUTPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise CapabilityToolFailed(
                "ffmpeg edit-state output escaped its project artifact boundary"
            ) from exc
        if validated_output != output_path or output_path.is_symlink():
            raise CapabilityToolFailed(
                "ffmpeg edit-state output must be a regular UV Studio-owned artifact file"
            )
        if not validated_output.is_file() or validated_output.stat().st_size <= 0:
            raise CapabilityToolFailed(
                "ffmpeg reported success but edit-state render output is empty or missing"
            )
        output_probe = adapter._probe_path(
            canonical_path=canonical_output,
            source=validated_output,
        )
        if _stream_count(output_probe, "video") != 1:
            raise CapabilityToolFailed(
                "ffmpeg edit-state output is not a single-video-stream clip"
            )
        if _stream_count(output_probe, "audio") != source_audio_count:
            raise CapabilityToolFailed(
                "ffmpeg edit-state output audio presence does not match the source"
            )
        if _video_geometry(output_probe) != source_geometry:
            raise CapabilityToolFailed(
                "ffmpeg edit-state output geometry changed unexpectedly"
            )
        actual_duration_us = _video_duration_us(output_probe)
        if actual_duration_us is None:
            raise CapabilityToolFailed(
                "ffmpeg edit-state output has no known positive video duration"
            )
        duration_delta_us = actual_duration_us - expected_duration_us
        if abs(duration_delta_us) > _FINAL_VIDEO_DURATION_TOLERANCE_US:
            raise CapabilityToolFailed(
                "ffmpeg edit-state output duration is inconsistent with accepted edit decisions"
            )

        artifact = ProjectReference(
            id=artifact_id,
            kind="video",
            path=canonical_output,
            metadata={
                "capability_id": offer.capability_id,
                "offer_id": offer.offer_id,
                "source_path": canonical_source,
                "edit_state_schema_version": state.schema_version,
                "edit_ids": [edit.edit_id for edit in edits],
                "replacement_paths": [path for path, _ in replacement_paths],
                "expected_output_video_duration_us": expected_duration_us,
                "actual_output_video_duration_us": actual_duration_us,
                "output_duration_delta_us": duration_delta_us,
                "composition_mode": _COMPOSITION_MODE,
                "audio_policy": _AUDIO_POLICY,
                "lifecycle": "render",
            },
        )
        project = adapter.store.load_project(project_id)
        adapter.store.update_project(
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
            "edit_ids": [edit.edit_id for edit in edits],
            "expected_output_video_duration_us": expected_duration_us,
            "actual_output_video_duration_us": actual_duration_us,
            "composition_mode": _COMPOSITION_MODE,
            "audio_policy": _AUDIO_POLICY,
        },
        artifact=artifact.to_dict(),
    )
