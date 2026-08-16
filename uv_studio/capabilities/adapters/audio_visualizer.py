"""Deterministic local waveform visualizer over project-owned audio and optional artwork."""

from __future__ import annotations

import hashlib
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.source_media import ProjectSourceMediaStore, SourceMediaError
from uv_studio.projects.store import ProjectStoreError

from ..execution import CapabilityExecutionResult, CapabilityToolFailed, InvalidCapabilityInput, UnsupportedCapabilityExecution
from ..models import CapabilityDefinition, CapabilityOffer, CostClass, LocalityClass, MediaKind, OfferAvailability, OperationKind
from ..registry import CapabilityRegistry

if TYPE_CHECKING:
    from .range_reinsertion import LocalFFmpegRangeAdapter

_CAPABILITY_ID = "audio.visualize"
_OFFER_ID = "local_ffmpeg.audio_visualize"
_OUTPUT_WIDTH = 1280
_OUTPUT_HEIGHT = 720
_OUTPUT_FPS = 30
_MODE = "project_audio_waveform_h264_aac"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def register_audio_visualizer_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _CAPABILITY_ID,
            "Аудиовизуализатор",
            (
                "Детерминированное H.264 MP4-представление зарегистрированной project-owned аудиодорожки "
                "как waveform, опционально поверх зарегистрированного изображения."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.AUDIO, MediaKind.IMAGE),
            (MediaKind.VIDEO,),
            asynchronous=False,
        )
    )
    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    registry.register_offer(
        CapabilityOffer(
            offer_id=_OFFER_ID,
            capability_id=_CAPABILITY_ID,
            adapter_id="local_ffmpeg",
            title="FFmpeg project-owned audio waveform visualizer",
            availability=OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE,
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; локальный waveform visualizer доступен."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=("audio.waveform", "video.h264", "audio.aac", "image.optional", "media.project_owned"),
        )
    )


def render_audio_visualizer(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _OFFER_ID:
        raise UnsupportedCapabilityExecution(
            f"audio visualizer requires exact offer {_OFFER_ID!r}"
        )
    allowed = {"audio_source_id", "artwork_source_id"}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported audio.visualize fields: {sorted(unknown)!r}"
        )
    raw_audio_id = payload.get("audio_source_id")
    if not isinstance(raw_audio_id, str) or not raw_audio_id.strip():
        raise InvalidCapabilityInput("audio.visualize requires non-empty string audio_source_id")
    audio_source_id = raw_audio_id.strip()
    raw_artwork_id = payload.get("artwork_source_id")
    if raw_artwork_id is not None and (
        not isinstance(raw_artwork_id, str) or not raw_artwork_id.strip()
    ):
        raise InvalidCapabilityInput("artwork_source_id must be a non-empty string when provided")
    artwork_source_id = raw_artwork_id.strip() if isinstance(raw_artwork_id, str) else None

    media_store = ProjectSourceMediaStore(adapter.store)
    try:
        audio_reference, audio_path = media_store.resolve_verified(
            project_id, audio_source_id, expected_kind="audio"
        )
        artwork_binding = (
            media_store.resolve_verified(project_id, artwork_source_id, expected_kind="image")
            if artwork_source_id is not None
            else None
        )
    except SourceMediaError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc

    expected_duration_us = audio_reference.metadata.get("duration_us")
    if (
        isinstance(expected_duration_us, bool)
        or not isinstance(expected_duration_us, int)
        or expected_duration_us <= 0
    ):
        raise InvalidCapabilityInput("registered audio source has no trusted positive duration")

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
        raise InvalidCapabilityInput("audio visualizer output path already exists")

    command = [adapter._tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-n"]
    if artwork_binding is None:
        command.extend(["-i", str(audio_path)])
        filter_complex = (
            f"[0:a]showwaves=s={_OUTPUT_WIDTH}x{_OUTPUT_HEIGHT}:mode=line:rate={_OUTPUT_FPS}:"
            "colors=white,format=yuv420p[v]"
        )
        audio_map = "0:a:0"
    else:
        command.extend(["-loop", "1", "-i", str(artwork_binding[1]), "-i", str(audio_path)])
        filter_complex = (
            f"[0:v]scale={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={_OUTPUT_FPS},setsar=1[bg];"
            f"[1:a]showwaves=s={_OUTPUT_WIDTH}x240:mode=line:rate={_OUTPUT_FPS}:"
            "colors=white,format=rgba[w];"
            "[bg][w]overlay=0:H-h-60:shortest=1,format=yuv420p[v]"
        )
        audio_map = "1:a:0"
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            audio_map,
            "-t",
            f"{expected_duration_us}us",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    try:
        adapter._invoke(command, timeout=adapter.assemble_timeout_sec, tool="ffmpeg")
        if not output_path.is_file() or output_path.is_symlink() or output_path.stat().st_size <= 0:
            raise CapabilityToolFailed("audio visualizer output is not a non-empty regular artifact")
        probe = adapter._probe_path(canonical_path=canonical_output, source=output_path)
        actual_duration_us = probe.get("duration_us")
        if (
            probe.get("has_video") is not True
            or probe.get("has_audio") is not True
            or not isinstance(actual_duration_us, int)
            or actual_duration_us <= 0
        ):
            raise CapabilityToolFailed("audio visualizer output must contain valid video and audio")
        tolerance_us = 200_000
        if abs(actual_duration_us - expected_duration_us) > tolerance_us:
            raise CapabilityToolFailed("audio visualizer duration does not match the registered master audio")

        artwork_metadata = None
        if artwork_binding is not None:
            reference = artwork_binding[0]
            artwork_metadata = {
                "source_id": reference.id,
                "path": reference.path,
                "sha256": reference.metadata.get("sha256"),
                "size_bytes": reference.metadata.get("size_bytes"),
            }
        artifact = ProjectReference(
            id=artifact_id,
            kind="video",
            path=canonical_output,
            metadata={
                "capability_id": offer.capability_id,
                "offer_id": offer.offer_id,
                "lifecycle": "audio_visualizer_render",
                "composition_mode": _MODE,
                "content_type": "video/mp4",
                "audio_binding": {
                    "source_id": audio_reference.id,
                    "path": audio_reference.path,
                    "sha256": audio_reference.metadata.get("sha256"),
                    "size_bytes": audio_reference.metadata.get("size_bytes"),
                },
                "artwork_binding": artwork_metadata,
                "expected_duration_us": expected_duration_us,
                "actual_duration_us": actual_duration_us,
                "sha256": _sha256_file(output_path),
                "size_bytes": output_path.stat().st_size,
                "width": _OUTPUT_WIDTH,
                "height": _OUTPUT_HEIGHT,
                "fps": _OUTPUT_FPS,
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
            "artifact_id": artifact_id,
            "composition_mode": _MODE,
            "duration_us": actual_duration_us,
        },
        artifact=artifact.to_dict(),
    )
