"""Deterministic local photo-to-video composition over project-owned still images."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import uuid
from collections.abc import Mapping
from decimal import Decimal
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

_CAPABILITY_ID = "video.compose_photos"
_OFFER_ID = "local_ffmpeg.video_compose_photos"
_MAX_IMAGES = 100
_MIN_IMAGE_DURATION_US = 250_000
_MAX_IMAGE_DURATION_US = 30_000_000
_OUTPUT_WIDTH = 1280
_OUTPUT_HEIGHT = 720
_OUTPUT_FPS = 30
_MODE = "project_stills_h264_optional_aac"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _concat_quote(path: Path) -> str:
    value = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{value}'\n"


def _duration_line(duration_us: int) -> str:
    seconds = Decimal(duration_us) / Decimal(1_000_000)
    return f"duration {seconds:.6f}\n"


def register_photo_slideshow_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _CAPABILITY_ID,
            "Фото в видео",
            (
                "Детерминированная сборка зарегистрированных project-owned неподвижных изображений "
                "в H.264 MP4 с фиксированной геометрией и опциональной project-owned аудиодорожкой."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.IMAGE, MediaKind.AUDIO),
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
            title="FFmpeg project-owned photo slideshow",
            availability=OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE,
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; локальная сборка фото в видео доступна."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=("image.sequence", "video.h264", "audio.optional", "media.project_owned"),
        )
    )


def compose_photo_slideshow(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _OFFER_ID:
        raise UnsupportedCapabilityExecution(
            f"photo slideshow requires exact offer {_OFFER_ID!r}"
        )
    allowed = {"image_source_ids", "audio_source_id", "duration_per_image_us"}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported video.compose_photos fields: {sorted(unknown)!r}"
        )
    raw_ids = payload.get("image_source_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise InvalidCapabilityInput("video.compose_photos requires non-empty image_source_ids array")
    if len(raw_ids) > _MAX_IMAGES:
        raise InvalidCapabilityInput(
            f"video.compose_photos supports at most {_MAX_IMAGES} images"
        )
    if any(not isinstance(item, str) or not item.strip() for item in raw_ids):
        raise InvalidCapabilityInput("every image_source_ids item must be a non-empty string")
    image_source_ids = [item.strip() for item in raw_ids]

    duration_us = payload.get("duration_per_image_us", 2_000_000)
    if isinstance(duration_us, bool) or not isinstance(duration_us, int):
        raise InvalidCapabilityInput("duration_per_image_us must be an integer")
    if not _MIN_IMAGE_DURATION_US <= duration_us <= _MAX_IMAGE_DURATION_US:
        raise InvalidCapabilityInput(
            f"duration_per_image_us must be between {_MIN_IMAGE_DURATION_US} and {_MAX_IMAGE_DURATION_US}"
        )

    raw_audio_id = payload.get("audio_source_id")
    if raw_audio_id is not None and (not isinstance(raw_audio_id, str) or not raw_audio_id.strip()):
        raise InvalidCapabilityInput("audio_source_id must be a non-empty string when provided")
    audio_source_id = raw_audio_id.strip() if isinstance(raw_audio_id, str) else None

    media_store = ProjectSourceMediaStore(adapter.store)
    image_bindings: list[tuple[ProjectReference, Path]] = []
    try:
        for source_id in image_source_ids:
            image_bindings.append(
                media_store.resolve_verified(project_id, source_id, expected_kind="image")
            )
        audio_binding = (
            media_store.resolve_verified(project_id, audio_source_id, expected_kind="audio")
            if audio_source_id is not None
            else None
        )
    except SourceMediaError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc

    total_duration_us = duration_us * len(image_bindings)
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
        raise InvalidCapabilityInput("photo slideshow output path already exists")

    tasks_dir = adapter.store.project_directory(project_id) / "tasks"
    manifest_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix="photo-slideshow-",
            suffix=".ffconcat",
            dir=tasks_dir,
            delete=False,
        ) as handle:
            manifest_path = Path(handle.name)
            handle.write("ffconcat version 1.0\n")
            for _reference, path in image_bindings:
                handle.write(_concat_quote(path))
                handle.write(_duration_line(duration_us))
            handle.write(_concat_quote(image_bindings[-1][1]))

        command = [
            adapter._tool("ffmpeg"),
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
        ]
        if audio_binding is not None:
            command.extend(["-i", str(audio_binding[1])])
        command.extend(
            [
                "-map",
                "0:v:0",
            ]
        )
        if audio_binding is not None:
            command.extend(["-map", "1:a:0"])
        command.extend(
            [
                "-vf",
                (
                    f"fps={_OUTPUT_FPS},scale={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:"
                    "force_original_aspect_ratio=decrease,"
                    f"pad={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
                    "setsar=1,format=yuv420p"
                ),
                "-t",
                f"{total_duration_us}us",
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
            ]
        )
        if audio_binding is not None:
            command.extend(["-af", "apad", "-c:a", "aac", "-b:a", "192k"])
        command.append(str(output_path))
        adapter._invoke(command, timeout=adapter.assemble_timeout_sec, tool="ffmpeg")

        if not output_path.is_file() or output_path.is_symlink() or output_path.stat().st_size <= 0:
            raise CapabilityToolFailed("photo slideshow output is not a non-empty regular artifact")
        probe = adapter._probe_path(canonical_path=canonical_output, source=output_path)
        actual_duration_us = probe.get("duration_us")
        if not probe.get("has_video") or not isinstance(actual_duration_us, int) or actual_duration_us <= 0:
            raise CapabilityToolFailed("photo slideshow output is not a valid video")
        tolerance_us = max(150_000, 2_000_000 // _OUTPUT_FPS)
        if abs(actual_duration_us - total_duration_us) > tolerance_us:
            raise CapabilityToolFailed("photo slideshow output duration does not match the requested composition")
        if audio_binding is not None and probe.get("has_audio") is not True:
            raise CapabilityToolFailed("photo slideshow output lost the requested audio track")

        image_metadata = [
            {
                "source_id": reference.id,
                "path": reference.path,
                "sha256": reference.metadata.get("sha256"),
                "size_bytes": reference.metadata.get("size_bytes"),
            }
            for reference, _path in image_bindings
        ]
        audio_metadata = None
        if audio_binding is not None:
            reference = audio_binding[0]
            audio_metadata = {
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
                "lifecycle": "photo_to_video_render",
                "composition_mode": _MODE,
                "content_type": "video/mp4",
                "image_bindings": image_metadata,
                "audio_binding": audio_metadata,
                "duration_per_image_us": duration_us,
                "expected_duration_us": total_duration_us,
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
    finally:
        if manifest_path is not None:
            manifest_path.unlink(missing_ok=True)

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
