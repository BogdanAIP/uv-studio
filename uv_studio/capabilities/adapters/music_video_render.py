"""Deterministic Stage 7 render from current Music Map/Director/Assembly state."""

from __future__ import annotations

import hashlib
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.music_assembly import MusicAssemblyError, MusicAssemblyStore
from uv_studio.projects.music_direction import MusicDirectionError, MusicDirectionStore
from uv_studio.projects.music_map import MusicMapError, MusicMapStore
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
from .range_reinsertion import (
    _audio_duration_us,
    _primary_stream,
    _stream_count,
    _video_duration_us,
)

if TYPE_CHECKING:
    from .range_reinsertion import LocalFFmpegRangeAdapter

_MUSIC_VIDEO_RENDER_CAPABILITY_ID = "video.render_music_video"
_MUSIC_VIDEO_RENDER_OFFER_ID = "local_ffmpeg.video_render_music_video"
_COMPOSITION_MODE = "music_assembly_visual_concat_with_exact_master_song_excerpt"
_OUTPUT_DURATION_TOLERANCE_US = 180_000
_OUTPUT_FPS = 30
_OUTPUT_AUDIO_RATE = 48_000


def register_music_video_render_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _MUSIC_VIDEO_RENDER_CAPABILITY_ID,
            "Рендер музыкального видео",
            (
                "Детерминированно материализует текущий Music Assembly Plan; визуальные "
                "источники используются без их аудио, а выбранный excerpt project-owned песни "
                "становится единственной финальной аудиодорожкой."
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
            offer_id=_MUSIC_VIDEO_RENDER_OFFER_ID,
            capability_id=_MUSIC_VIDEO_RENDER_CAPABILITY_ID,
            adapter_id="local_ffmpeg",
            title="FFmpeg canonical Music Video render",
            availability=(
                OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE
            ),
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; локальный Music Video render доступен."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=(
                "video.music_video",
                "timeline.music_assembly",
                "audio.master_song",
                "video.normalized_concat",
            ),
        )
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _even_dimension(value: Any, *, fallback: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        value = fallback
    value = min(value, maximum)
    if value % 2:
        value -= 1
    return max(2, value)


def _video_filter(
    *,
    input_index: int,
    start_us: int,
    end_us: int,
    width: int,
    height: int,
) -> str:
    return (
        f"[{input_index}:v:0]"
        f"trim=start={start_us}us:end={end_us}us,"
        "setpts=PTS-STARTPTS,"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"fps={_OUTPUT_FPS},format=yuv420p[v{input_index}]"
    )


def render_music_video_state(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _MUSIC_VIDEO_RENDER_OFFER_ID:
        raise UnsupportedCapabilityExecution(
            f"music video render requires exact offer {_MUSIC_VIDEO_RENDER_OFFER_ID!r}"
        )
    unknown = set(payload).difference({"assembly_revision_sha256"})
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported video.render_music_video fields: {sorted(unknown)!r}"
        )
    requested_revision = payload.get("assembly_revision_sha256")
    if not isinstance(requested_revision, str) or len(requested_revision) != 64:
        raise InvalidCapabilityInput(
            "video.render_music_video requires 64-character assembly_revision_sha256"
        )
    try:
        int(requested_revision, 16)
    except ValueError as exc:
        raise InvalidCapabilityInput(
            "video.render_music_video requires hexadecimal assembly_revision_sha256"
        ) from exc

    try:
        assembly = MusicAssemblyStore(adapter.store).load(project_id, validate_current=True)
        if assembly is None:
            raise InvalidCapabilityInput(
                "video.render_music_video requires a current Music Assembly Plan"
            )
        if assembly.revision_sha256 != requested_revision.lower():
            raise InvalidCapabilityInput(
                "video.render_music_video was requested for a stale Music Assembly revision"
            )
        direction_store = MusicDirectionStore(adapter.store)
        direction = direction_store.load(project_id, validate_current=True)
        music_map = MusicMapStore(adapter.store).load(project_id, validate_current=True)
        if direction is None or music_map is None:
            raise InvalidCapabilityInput(
                "video.render_music_video requires current Music Map and Music Director state"
            )
        if assembly.music_direction_revision_sha256 != direction.revision_sha256:
            raise InvalidCapabilityInput(
                "Music Assembly Plan no longer matches current Music Director revision"
            )
        rhythm_audit = direction_store.rhythm_audit(project_id)
        if rhythm_audit.get("summary", {}).get("all_aligned") is not True:
            raise InvalidCapabilityInput(
                "video.render_music_video requires current Music Director rhythm audit to be fully aligned"
            )

        sources = ProjectSourceMediaStore(adapter.store)
        song_ref, song_path = sources.resolve_verified(
            project_id, music_map.song.reference_id, expected_kind="audio"
        )
        if (
            song_ref.path != music_map.song.reference_path
            or song_ref.metadata.get("sha256") != music_map.song.sha256
            or song_ref.metadata.get("size_bytes") != music_map.song.size_bytes
        ):
            raise InvalidCapabilityInput("current song bytes no longer match Music Map binding")

        visual_inputs: list[tuple[Any, Path, dict[str, Any]]] = []
        for binding in assembly.bindings:
            reference, path = sources.resolve_verified(
                project_id, binding.source_id, expected_kind="video"
            )
            if (
                reference.path != binding.source_path
                or reference.metadata.get("sha256") != binding.source_sha256
                or reference.metadata.get("size_bytes") != binding.source_size_bytes
            ):
                raise InvalidCapabilityInput(
                    f"visual bytes for shot {binding.shot_id!r} no longer match Music Assembly binding"
                )
            probe = adapter._probe_path(canonical_path=reference.path, source=path)
            if _stream_count(probe, "video") != 1:
                raise InvalidCapabilityInput(
                    f"visual source for shot {binding.shot_id!r} must contain exactly one video stream"
                )
            actual_duration_us = _video_duration_us(probe)
            if actual_duration_us is None or binding.source_end_us > actual_duration_us:
                raise InvalidCapabilityInput(
                    f"visual source for shot {binding.shot_id!r} is shorter than its bound interval"
                )
            visual_inputs.append((binding, path, probe))

        song_probe = adapter._probe_path(canonical_path=song_ref.path, source=song_path)
        if _stream_count(song_probe, "audio") != 1 or _stream_count(song_probe, "video") != 0:
            raise InvalidCapabilityInput(
                "Music Map master song must contain exactly one audio stream and no video"
            )
        actual_song_duration_us = _audio_duration_us(song_probe)
        if actual_song_duration_us is None or music_map.excerpt.end_us > actual_song_duration_us:
            raise InvalidCapabilityInput(
                "Music Map excerpt exceeds the actual ffprobe duration of current song bytes"
            )
    except InvalidCapabilityInput:
        raise
    except (
        MusicAssemblyError,
        MusicDirectionError,
        MusicMapError,
        SourceMediaError,
        ProjectValidationError,
        ProjectStoreError,
    ) as exc:
        raise InvalidCapabilityInput(str(exc)) from exc

    first_video = _primary_stream(visual_inputs[0][2], "video") or {}
    width = _even_dimension(first_video.get("width"), fallback=1280, maximum=3840)
    height = _even_dimension(first_video.get("height"), fallback=720, maximum=2160)

    filters = [
        _video_filter(
            input_index=index,
            start_us=binding.source_start_us,
            end_us=binding.source_end_us,
            width=width,
            height=height,
        )
        for index, (binding, _path, _probe) in enumerate(visual_inputs)
    ]
    visual_labels = "".join(f"[v{index}]" for index in range(len(visual_inputs)))
    filters.append(
        f"{visual_labels}concat=n={len(visual_inputs)}:v=1:a=0[vout]"
    )
    song_input_index = len(visual_inputs)
    filters.append(
        f"[{song_input_index}:a:0]"
        f"atrim=start={music_map.excerpt.start_us}us:end={music_map.excerpt.end_us}us,"
        f"asetpts=PTS-STARTPTS,aresample={_OUTPUT_AUDIO_RATE}[aout]"
    )
    filter_graph = ";".join(filters)

    artifact_id = f"art_{uuid.uuid4().hex}"
    canonical_output = f"artifacts/{artifact_id}.mp4"
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
            f"video.render_music_video refuses to overwrite existing output: {canonical_output!r}"
        )

    command = [
        adapter._tool("ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
    ]
    for _binding, path, _probe in visual_inputs:
        command.extend(["-i", str(path)])
    command.extend(["-i", str(song_path)])
    command.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]
    )

    expected_duration_us = music_map.excerpt.duration_us
    try:
        adapter._invoke(command, timeout=adapter.assemble_timeout_sec, tool="ffmpeg")
        validated = adapter.store.resolve_project_file(
            project_id,
            canonical_output,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        if validated != output_path or output_path.is_symlink() or not output_path.is_file():
            raise CapabilityToolFailed(
                "music video output must be a regular UV Studio-owned artifact file"
            )
        output_size = output_path.stat().st_size
        if output_size <= 0:
            raise CapabilityToolFailed("ffmpeg reported success but music video output is empty")
        output_probe = adapter._probe_path(canonical_path=canonical_output, source=validated)
        if _stream_count(output_probe, "video") != 1 or _stream_count(output_probe, "audio") != 1:
            raise CapabilityToolFailed(
                "music video render output must contain exactly one video and one audio stream"
            )
        output_video_duration_us = _video_duration_us(output_probe)
        output_audio_duration_us = _audio_duration_us(output_probe)
        if output_video_duration_us is None or output_audio_duration_us is None:
            raise CapabilityToolFailed(
                "music video render output requires known video/audio durations"
            )
        if abs(output_video_duration_us - expected_duration_us) > _OUTPUT_DURATION_TOLERANCE_US:
            raise CapabilityToolFailed(
                "music video render duration does not match selected Music Map excerpt"
            )
        if abs(output_audio_duration_us - expected_duration_us) > _OUTPUT_DURATION_TOLERANCE_US:
            raise CapabilityToolFailed(
                "music video master audio duration does not match selected Music Map excerpt"
            )

        output_sha256 = _sha256_file(output_path)
        artifact = ProjectReference(
            id=artifact_id,
            kind="video",
            path=canonical_output,
            metadata={
                "capability_id": offer.capability_id,
                "offer_id": offer.offer_id,
                "composition_mode": _COMPOSITION_MODE,
                "music_map_revision_sha256": music_map.revision_sha256,
                "music_direction_revision_sha256": direction.revision_sha256,
                "music_assembly_revision_sha256": assembly.revision_sha256,
                "song_reference_id": music_map.song.reference_id,
                "song_sha256": music_map.song.sha256,
                "song_excerpt": music_map.excerpt.to_dict(),
                "visual_bindings": [item.to_dict() for item in assembly.bindings],
                "width": width,
                "height": height,
                "fps": _OUTPUT_FPS,
                "size_bytes": output_size,
                "sha256": output_sha256,
                "actual_output_video_duration_us": output_video_duration_us,
                "actual_output_audio_duration_us": output_audio_duration_us,
                "lifecycle": "music_video_render",
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
            "composition_mode": _COMPOSITION_MODE,
            "music_map_revision_sha256": music_map.revision_sha256,
            "music_direction_revision_sha256": direction.revision_sha256,
            "music_assembly_revision_sha256": assembly.revision_sha256,
            "song_reference_id": music_map.song.reference_id,
            "song_excerpt": music_map.excerpt.to_dict(),
            "visual_shot_ids": [item.shot_id for item in assembly.bindings],
            "actual_output_video_duration_us": output_video_duration_us,
            "actual_output_audio_duration_us": output_audio_duration_us,
        },
        artifact=artifact.to_dict(),
    )
