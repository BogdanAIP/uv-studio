"""Deterministic Stage 5 render of accepted dubbing over the canonical edit timeline."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from uv_studio.projects.dubbing_review import DubbingReviewError, DubbingReviewStore
from uv_studio.projects.edit_state import EditStateError, RangeEditStateStore
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.prepared_audio import PreparedAudioError, ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore, SourceMediaError
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
from .edit_render import render_edit_state
from .range_reinsertion import (
    _FINAL_VIDEO_DURATION_TOLERANCE_US,
    _audio_duration_us,
    _primary_stream,
    _stream_count,
    _video_duration_us,
)

if TYPE_CHECKING:
    from .range_reinsertion import LocalFFmpegRangeAdapter

_DUBBING_RENDER_CAPABILITY_ID = "video.render_dubbing"
_DUBBING_RENDER_OFFER_ID = "local_ffmpeg.video_render_dubbing"
_VISUAL_RENDER_OFFER_ID = "local_ffmpeg.video_render_edits"
_SUPPORTED_POLICY = "replace_source_audio_range"
_COMPOSITION_MODE = "canonical_visual_master_then_exact_dubbing_audio_concat"
_TIME_MAPPING_MODE = "source_time_plus_preceding_visual_edit_duration_deltas"


def register_dubbing_render_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _DUBBING_RENDER_CAPABILITY_ID,
            "Рендер принятого дубляжа",
            (
                "Детерминированно материализует текущие принятые визуальные правки и "
                "принятую озвучку одного project-owned source без клиентских путей и таймкодов."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.VIDEO, MediaKind.AUDIO, MediaKind.TIMELINE),
            (MediaKind.VIDEO,),
            asynchronous=False,
        )
    )
    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    registry.register_offer(
        CapabilityOffer(
            offer_id=_DUBBING_RENDER_OFFER_ID,
            capability_id=_DUBBING_RENDER_CAPABILITY_ID,
            adapter_id="local_ffmpeg",
            title="FFmpeg accepted dubbing render",
            availability=(
                OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE
            ),
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; локальный рендер принятого дубляжа доступен."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=(
                "video.dubbing",
                "audio.replace_range",
                "timeline.accepted_state",
                "video.lossless_intermediate",
            ),
        )
    )


def _visual_render_offer() -> CapabilityOffer:
    return CapabilityOffer(
        offer_id=_VISUAL_RENDER_OFFER_ID,
        capability_id="video.render_edits",
        adapter_id="local_ffmpeg",
        title="internal canonical visual render",
        availability=OfferAvailability.AVAILABLE,
        reason="internal composition step after current accepted edit validation",
        locality=LocalityClass.LOCAL,
        cost_class=CostClass.FREE,
        asynchronous=False,
    )


def _ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and end_a > start_b


def _layout_for_stream(stream: Mapping[str, Any] | None) -> tuple[int, str]:
    if stream is None:
        return 48_000, "stereo"
    raw_rate = stream.get("sample_rate")
    try:
        sample_rate = int(raw_rate)
    except (TypeError, ValueError) as exc:
        raise InvalidCapabilityInput(
            "video.render_dubbing requires a known positive source audio sample_rate"
        ) from exc
    if sample_rate <= 0:
        raise InvalidCapabilityInput(
            "video.render_dubbing requires a known positive source audio sample_rate"
        )
    layout = stream.get("channel_layout")
    if isinstance(layout, str) and layout.strip():
        return sample_rate, layout.strip()
    channels = stream.get("channels")
    if channels == 1:
        return sample_rate, "mono"
    if channels == 2:
        return sample_rate, "stereo"
    raise InvalidCapabilityInput(
        "video.render_dubbing requires source channel_layout for audio with more than two channels"
    )


def _source_to_master_time_us(
    value_us: int,
    visual_edits: tuple[Any, ...],
    replacement_durations_us: tuple[int, ...],
) -> int:
    delta = 0
    for edit, replacement_duration_us in zip(visual_edits, replacement_durations_us):
        if edit.end_us <= value_us:
            delta += replacement_duration_us - edit.duration_us
        else:
            break
    return value_us + delta


def _audio_filter_graph(
    *,
    mapped_edits: tuple[tuple[Any, int, int], ...],
    master_duration_us: int,
    has_source_audio: bool,
    sample_rate: int,
    channel_layout: str,
) -> str:
    filters: list[str] = []
    labels: list[str] = []
    cursor_us = 0
    label_index = 0

    def add_source_segment(start_us: int, end_us: int) -> None:
        nonlocal label_index
        if end_us <= start_us:
            return
        label = f"a{label_index}"
        duration_us = end_us - start_us
        if has_source_audio:
            filters.append(
                f"[0:a:0]atrim=start={start_us}us:end={end_us}us,"
                f"asetpts=PTS-STARTPTS,aresample={sample_rate},"
                f"aformat=sample_rates={sample_rate}:channel_layouts={channel_layout}[{label}]"
            )
        else:
            filters.append(
                f"anullsrc=r={sample_rate}:cl={channel_layout},"
                f"atrim=duration={duration_us}us,asetpts=PTS-STARTPTS[{label}]"
            )
        labels.append(label)
        label_index += 1

    def add_dubbing_segment(input_index: int, duration_us: int) -> None:
        nonlocal label_index
        label = f"a{label_index}"
        filters.append(
            f"[{input_index}:a:0]aresample={sample_rate},"
            f"aformat=sample_rates={sample_rate}:channel_layouts={channel_layout},"
            f"apad,atrim=duration={duration_us}us,asetpts=PTS-STARTPTS[{label}]"
        )
        labels.append(label)
        label_index += 1

    for input_index, (_edit, start_us, end_us) in enumerate(mapped_edits, start=1):
        add_source_segment(cursor_us, start_us)
        add_dubbing_segment(input_index, end_us - start_us)
        cursor_us = end_us
    add_source_segment(cursor_us, master_duration_us)

    if not labels:
        raise InvalidCapabilityInput("video.render_dubbing produced no audio timeline segments")
    if len(labels) == 1:
        filters.append(f"[{labels[0]}]anull[aout]")
    else:
        inputs = "".join(f"[{label}]" for label in labels)
        filters.append(f"{inputs}concat=n={len(labels)}:v=0:a=1[aout]")
    return ";".join(filters)


def render_dubbing_state(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _DUBBING_RENDER_OFFER_ID:
        raise UnsupportedCapabilityExecution(
            f"dubbing render requires exact offer {_DUBBING_RENDER_OFFER_ID!r}"
        )
    unknown = set(payload).difference({"source_id"})
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported video.render_dubbing fields: {sorted(unknown)!r}"
        )
    source_id = payload.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise InvalidCapabilityInput("video.render_dubbing requires non-empty string field 'source_id'")

    try:
        source_store = ProjectSourceMediaStore(adapter.store)
        source_ref, source_file = source_store.resolve_verified(project_id, source_id.strip())
        source_sha256 = source_ref.metadata.get("sha256")
        if not isinstance(source_sha256, str) or len(source_sha256) != 64:
            raise InvalidCapabilityInput("registered source is missing a valid sha256")

        accepted_state = DubbingReviewStore(adapter.store).load_accepted(
            project_id, validate_current=True
        )
        dubbing_edits = tuple(
            sorted(
                (item for item in accepted_state.edits if item.source_id == source_ref.id),
                key=lambda item: (item.target_start_us, item.target_end_us, item.accepted_id),
            )
        )
        if not dubbing_edits:
            raise InvalidCapabilityInput(
                "video.render_dubbing requires at least one current accepted dubbing edit for source_id"
            )
        for item in dubbing_edits:
            if item.source_sha256 != source_sha256:
                raise InvalidCapabilityInput(
                    f"accepted dubbing edit {item.accepted_id!r} is stale for current source bytes"
                )
            if item.composition_policy != _SUPPORTED_POLICY:
                raise InvalidCapabilityInput(
                    f"composition policy {item.composition_policy!r} is not executable yet; "
                    f"current deterministic render supports only {_SUPPORTED_POLICY!r}"
                )
        previous = None
        for item in dubbing_edits:
            if previous is not None and item.target_start_us < previous.target_end_us:
                raise InvalidCapabilityInput(
                    "accepted dubbing ranges for one source must not overlap: "
                    f"{previous.accepted_id!r} and {item.accepted_id!r}"
                )
            previous = item

        visual_state = RangeEditStateStore(adapter.store).load(
            project_id, validate_references=True
        )
        visual_edits = visual_state.for_source(source_ref.path)
        for dubbing in dubbing_edits:
            for visual in visual_edits:
                if _ranges_overlap(
                    dubbing.target_start_us,
                    dubbing.target_end_us,
                    visual.start_us,
                    visual.end_us,
                ):
                    raise InvalidCapabilityInput(
                        "accepted dubbing currently cannot overlap an accepted visual replacement; "
                        f"dubbing={dubbing.accepted_id!r}, visual={visual.edit_id!r}"
                    )
    except InvalidCapabilityInput:
        raise
    except (
        SourceMediaError,
        DubbingReviewError,
        EditStateError,
        PreparedAudioError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise InvalidCapabilityInput(str(exc)) from exc

    replacement_durations: list[int] = []
    for visual in visual_edits:
        canonical_replacement, replacement_file = adapter._resolve_input_file(
            project_id,
            visual.replacement_path,
            operation=f"video.render_dubbing visual replacement {visual.edit_id}",
        )
        probe = adapter._probe_path(
            canonical_path=canonical_replacement,
            source=replacement_file,
        )
        duration_us = _video_duration_us(probe)
        if duration_us is None:
            raise InvalidCapabilityInput(
                f"accepted visual replacement {visual.edit_id!r} has no known positive duration"
            )
        replacement_durations.append(duration_us)

    if visual_edits:
        visual_result = render_edit_state(
            adapter,
            project_id=project_id,
            offer=_visual_render_offer(),
            payload={"source_path": source_ref.path},
        )
        master_path = visual_result.output["path"]
        master_canonical, master_file = adapter._resolve_input_file(
            project_id,
            master_path,
            operation="video.render_dubbing visual master",
        )
    else:
        master_path = source_ref.path
        master_canonical = source_ref.path
        master_file = source_file

    master_probe = adapter._probe_path(canonical_path=master_canonical, source=master_file)
    if _stream_count(master_probe, "video") != 1:
        raise InvalidCapabilityInput("video.render_dubbing requires a single-video-stream master")
    source_audio_count = _stream_count(master_probe, "audio")
    if source_audio_count > 1:
        raise InvalidCapabilityInput("video.render_dubbing currently supports at most one master audio stream")
    master_duration_us = _video_duration_us(master_probe)
    if master_duration_us is None:
        raise InvalidCapabilityInput("video.render_dubbing requires known positive master duration")
    sample_rate, channel_layout = _layout_for_stream(
        _primary_stream(master_probe, "audio") if source_audio_count else None
    )

    prepared_audio = ProjectPreparedAudioStore(adapter.store)
    audio_inputs: list[tuple[str, Any]] = []
    mapped: list[tuple[Any, int, int]] = []
    for item in dubbing_edits:
        try:
            audio_ref, audio_file = prepared_audio.resolve_verified(project_id, item.audio_id)
        except (PreparedAudioError, ProjectStoreError, ProjectValidationError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        if audio_ref.metadata.get("sha256") != item.audio_sha256:
            raise InvalidCapabilityInput(
                f"accepted dubbing edit {item.accepted_id!r} audio bytes changed after review"
            )
        audio_probe = adapter._probe_path(canonical_path=audio_ref.path, source=audio_file)
        if _stream_count(audio_probe, "audio") != 1 or _stream_count(audio_probe, "video") != 0:
            raise InvalidCapabilityInput(
                f"accepted dubbing audio {item.audio_id!r} must contain exactly one audio stream and no video"
            )
        mapped_start = _source_to_master_time_us(
            item.target_start_us,
            visual_edits,
            tuple(replacement_durations),
        )
        mapped_end = _source_to_master_time_us(
            item.target_end_us,
            visual_edits,
            tuple(replacement_durations),
        )
        if mapped_start < 0 or mapped_end <= mapped_start or mapped_end > master_duration_us:
            raise InvalidCapabilityInput(
                f"accepted dubbing edit {item.accepted_id!r} maps outside the materialized visual timeline"
            )
        audio_inputs.append((audio_ref.path, audio_file))
        mapped.append((item, mapped_start, mapped_end))

    artifact_id = f"art_{uuid.uuid4().hex}"
    canonical_output = f"artifacts/{artifact_id}.mkv"
    try:
        output_path = adapter.store.resolve_project_file(
            project_id,
            canonical_output,
            must_exist=False,
            allowed_roots=("artifacts",),
        )
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    if output_path.exists() or output_path.is_symlink():
        raise InvalidCapabilityInput(
            f"video.render_dubbing refuses to overwrite existing output: {canonical_output!r}"
        )

    filter_graph = _audio_filter_graph(
        mapped_edits=tuple(mapped),
        master_duration_us=master_duration_us,
        has_source_audio=source_audio_count == 1,
        sample_rate=sample_rate,
        channel_layout=channel_layout,
    )
    command = [
        adapter._tool("ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-i",
        str(master_file),
    ]
    for _canonical, path in audio_inputs:
        command.extend(["-i", str(path)])
    command.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "flac",
            str(output_path),
        ]
    )

    try:
        adapter._invoke(command, timeout=adapter.extract_timeout_sec, tool="ffmpeg")
        validated = adapter.store.resolve_project_file(
            project_id,
            canonical_output,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        if validated != output_path or output_path.is_symlink() or not output_path.is_file():
            raise CapabilityToolFailed(
                "ffmpeg dubbing output must be a regular UV Studio-owned artifact file"
            )
        if output_path.stat().st_size <= 0:
            raise CapabilityToolFailed("ffmpeg reported success but dubbing output is empty")
        output_probe = adapter._probe_path(canonical_path=canonical_output, source=validated)
        if _stream_count(output_probe, "video") != 1 or _stream_count(output_probe, "audio") != 1:
            raise CapabilityToolFailed("dubbing render output must contain one video and one audio stream")
        output_video_duration_us = _video_duration_us(output_probe)
        output_audio_duration_us = _audio_duration_us(output_probe)
        if output_video_duration_us is None or output_audio_duration_us is None:
            raise CapabilityToolFailed("dubbing render output requires known video/audio durations")
        if abs(output_video_duration_us - master_duration_us) > _FINAL_VIDEO_DURATION_TOLERANCE_US:
            raise CapabilityToolFailed("dubbing render changed the materialized video duration")
        if abs(output_audio_duration_us - master_duration_us) > _FINAL_VIDEO_DURATION_TOLERANCE_US:
            raise CapabilityToolFailed("dubbing render audio duration does not match materialized video")

        artifact = ProjectReference(
            id=artifact_id,
            kind="video",
            path=canonical_output,
            metadata={
                "capability_id": offer.capability_id,
                "offer_id": offer.offer_id,
                "source_id": source_ref.id,
                "source_path": source_ref.path,
                "source_sha256": source_sha256,
                "visual_master_path": master_path,
                "visual_edit_ids": [item.edit_id for item in visual_edits],
                "accepted_dubbing_ids": [item.accepted_id for item in dubbing_edits],
                "composition_policies": sorted({item.composition_policy for item in dubbing_edits}),
                "composition_mode": _COMPOSITION_MODE,
                "time_mapping_mode": _TIME_MAPPING_MODE,
                "mapped_ranges": [
                    {
                        "accepted_id": item.accepted_id,
                        "source_start_us": item.target_start_us,
                        "source_end_us": item.target_end_us,
                        "master_start_us": start_us,
                        "master_end_us": end_us,
                    }
                    for item, start_us, end_us in mapped
                ],
                "actual_output_video_duration_us": output_video_duration_us,
                "actual_output_audio_duration_us": output_audio_duration_us,
                "lifecycle": "dubbing_render",
            },
        )
        project = adapter.store.load_project(project_id)
        adapter.store.update_project(project_id, artifacts=(*project.artifacts, artifact))
    except Exception:
        output_path.unlink(missing_ok=True)
        raise

    return CapabilityExecutionResult.from_offer(
        project_id=project_id,
        offer=offer,
        output={
            "path": canonical_output,
            "source_id": source_ref.id,
            "visual_edit_ids": [item.edit_id for item in visual_edits],
            "accepted_dubbing_ids": [item.accepted_id for item in dubbing_edits],
            "composition_mode": _COMPOSITION_MODE,
            "time_mapping_mode": _TIME_MAPPING_MODE,
            "actual_output_video_duration_us": output_video_duration_us,
            "actual_output_audio_duration_us": output_audio_duration_us,
        },
        artifact=artifact.to_dict(),
    )
