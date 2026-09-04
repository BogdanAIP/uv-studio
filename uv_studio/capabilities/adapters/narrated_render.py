"""Deterministic local render of the current Narrated workspace and prepared speech."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import uuid
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from uv_studio.projects.models import (
    ProjectReference,
    ProjectValidationError,
    compatibility_recipe_id,
)
from uv_studio.projects.prepared_audio import PreparedAudioError, ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore, SourceMediaError
from uv_studio.projects.stage8_workspace import Stage8WorkspaceError, get_stage8_workspace
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

if TYPE_CHECKING:
    from .range_reinsertion import LocalFFmpegRangeAdapter

_CAPABILITY_ID = "video.render_narrated"
_OFFER_ID = "local_ffmpeg.video_render_narrated"
_RECIPE_ID = "narrated_video"
_LIFECYCLE = "narrated_video_render"
_MODE = "narrated_workspace_stills_with_prepared_speech"
_MAX_IMAGES = 100
_MIN_IMAGE_DURATION_US = 100_000
_OUTPUT_WIDTH = 1280
_OUTPUT_HEIGHT = 720
_OUTPUT_FPS = 30


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _concat_quote(path: Path) -> str:
    value = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{value}'\n"


def _duration_line(duration_us: int) -> str:
    seconds = Decimal(duration_us) / Decimal(1_000_000)
    return f"duration {seconds:.6f}\n"


def register_narrated_render_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _CAPABILITY_ID,
            "Рендер видео с диктором",
            (
                "Детерминированно собирает текущие SHA-привязанные изображения Narrated workspace "
                "и verified project-owned prepared speech в H.264/AAC мастер."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.IMAGE, MediaKind.AUDIO, MediaKind.TIMELINE),
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
            title="FFmpeg Narrated workspace render",
            availability=OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE,
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; локальный Narrated render доступен."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=(
                "narrated.workspace_revision",
                "narrated.prepared_speech",
                "image.sequence",
                "video.h264",
                "audio.aac",
                "media.project_owned",
            ),
        )
    )


def render_narrated_workspace(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _OFFER_ID or offer.capability_id != _CAPABILITY_ID:
        raise UnsupportedCapabilityExecution(
            f"Narrated render requires exact offer {_OFFER_ID!r}"
        )
    allowed = {"workspace_revision_sha256", "audio_id"}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported video.render_narrated fields: {sorted(unknown)!r}"
        )
    revision = payload.get("workspace_revision_sha256")
    audio_id = payload.get("audio_id")
    if not isinstance(revision, str) or len(revision) != 64:
        raise InvalidCapabilityInput("video.render_narrated requires workspace_revision_sha256")
    if not isinstance(audio_id, str) or not audio_id.strip():
        raise InvalidCapabilityInput("video.render_narrated requires non-empty audio_id")
    audio_id = audio_id.strip()

    project = adapter.store.load_project(project_id)
    if compatibility_recipe_id(project) != _RECIPE_ID:
        raise InvalidCapabilityInput("video.render_narrated is available only for narrated_video")
    try:
        workspace = get_stage8_workspace(adapter.store, project_id)
    except Stage8WorkspaceError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    if workspace is None:
        raise InvalidCapabilityInput("Narrated workspace is not saved")
    if workspace.revision_sha256 != revision:
        raise InvalidCapabilityInput("Narrated workspace revision is stale")
    if not workspace.script:
        raise InvalidCapabilityInput("Narrated workspace requires a non-empty script before render")

    image_bindings = tuple(item for item in workspace.sources if item.kind == "image")
    if not image_bindings:
        raise InvalidCapabilityInput("Narrated render requires at least one workspace image")
    if len(image_bindings) > _MAX_IMAGES:
        raise InvalidCapabilityInput(f"Narrated render supports at most {_MAX_IMAGES} images")

    source_media = ProjectSourceMediaStore(adapter.store)
    verified_images: list[tuple[ProjectReference, Path]] = []
    try:
        for binding in image_bindings:
            reference, path = source_media.resolve_verified(
                project_id,
                binding.source_id,
                expected_kind="image",
            )
            if (
                reference.path != binding.path
                or reference.metadata.get("sha256") != binding.sha256
                or reference.metadata.get("size_bytes") != binding.size_bytes
            ):
                raise InvalidCapabilityInput("Narrated image binding is stale or corrupted")
            verified_images.append((reference, path))
    except SourceMediaError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc

    prepared_audio = ProjectPreparedAudioStore(adapter.store)
    try:
        audio_reference, audio_path = prepared_audio.resolve_verified(project_id, audio_id)
    except PreparedAudioError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    duration_us = audio_reference.metadata.get("duration_us")
    if isinstance(duration_us, bool) or not isinstance(duration_us, int) or duration_us <= 0:
        raise InvalidCapabilityInput("prepared narration has no trusted positive duration_us")
    if duration_us < len(verified_images) * _MIN_IMAGE_DURATION_US:
        raise InvalidCapabilityInput(
            "prepared narration is too short for the number of selected workspace images"
        )

    base_duration, remainder = divmod(duration_us, len(verified_images))
    image_durations = tuple(
        base_duration + (1 if index < remainder else 0)
        for index in range(len(verified_images))
    )

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
        raise InvalidCapabilityInput("Narrated render output path already exists")

    tasks_dir = adapter.store.project_directory(project_id) / "tasks"
    manifest_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix="narrated-render-",
            suffix=".ffconcat",
            dir=tasks_dir,
            delete=False,
        ) as handle:
            manifest_path = Path(handle.name)
            handle.write("ffconcat version 1.0\n")
            for (_reference, path), item_duration_us in zip(verified_images, image_durations):
                handle.write(_concat_quote(path))
                handle.write(_duration_line(item_duration_us))
            handle.write(_concat_quote(verified_images[-1][1]))

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
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            (
                f"fps={_OUTPUT_FPS},scale={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
                "setsar=1,format=yuv420p"
            ),
            "-t",
            f"{duration_us}us",
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
        adapter._invoke(command, timeout=adapter.assemble_timeout_sec, tool="ffmpeg")
        if not output_path.is_file() or output_path.is_symlink() or output_path.stat().st_size <= 0:
            raise CapabilityToolFailed("Narrated render output is not a non-empty regular artifact")
        probe = adapter._probe_path(canonical_path=canonical_output, source=output_path)
        actual_duration_us = probe.get("duration_us")
        if (
            probe.get("has_video") is not True
            or probe.get("has_audio") is not True
            or not isinstance(actual_duration_us, int)
            or actual_duration_us <= 0
        ):
            raise CapabilityToolFailed("Narrated render output is not a valid audiovisual master")
        tolerance_us = max(150_000, 2_000_000 // _OUTPUT_FPS)
        if abs(actual_duration_us - duration_us) > tolerance_us:
            raise CapabilityToolFailed("Narrated render duration does not match prepared speech")

        image_metadata = [
            {
                "source_id": reference.id,
                "path": reference.path,
                "sha256": reference.metadata.get("sha256"),
                "size_bytes": reference.metadata.get("size_bytes"),
            }
            for reference, _path in verified_images
        ]
        audio_metadata = {
            "audio_id": audio_reference.id,
            "path": audio_reference.path,
            "sha256": audio_reference.metadata.get("sha256"),
            "size_bytes": audio_reference.metadata.get("size_bytes"),
            "duration_us": duration_us,
            "origin": audio_reference.metadata.get("origin"),
        }
        artifact = ProjectReference(
            id=artifact_id,
            kind="video",
            path=canonical_output,
            metadata={
                "capability_id": offer.capability_id,
                "offer_id": offer.offer_id,
                "lifecycle": _LIFECYCLE,
                "composition_mode": _MODE,
                "workspace_revision_sha256": workspace.revision_sha256,
                "image_bindings": image_metadata,
                "audio_binding": audio_metadata,
                "expected_duration_us": duration_us,
                "actual_duration_us": actual_duration_us,
                "content_type": "video/mp4",
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
            "workspace_revision_sha256": workspace.revision_sha256,
            "audio_id": audio_reference.id,
            "composition_mode": _MODE,
            "duration_us": actual_duration_us,
        },
        artifact=artifact.to_dict(),
    )
