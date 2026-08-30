"""Deterministic local render of the current General Video Stage 8 workspace."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from uv_studio.projects.models import (
    ProjectReference,
    ProjectValidationError,
    compatibility_recipe_id,
)
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

_CAPABILITY_ID = "video.render_general"
_OFFER_ID = "local_ffmpeg.video_render_general"
_RECIPE_ID = "general_video"
_LIFECYCLE = "general_video_render"
_MODE = "general_workspace_ordered_visuals"
_MAX_VISUALS = 100
_IMAGE_DURATION_US = 2_000_000
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


def _video_filter() -> str:
    return (
        f"fps={_OUTPUT_FPS},scale={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={_OUTPUT_WIDTH}:{_OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,format=yuv420p"
    )


def register_general_video_render_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _CAPABILITY_ID,
            "Рендер обычного видеоролика",
            (
                "Детерминированно собирает упорядоченные SHA-привязанные изображения и видео "
                "текущего General Video workspace, опционально с одной project-owned аудиодорожкой."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.IMAGE, MediaKind.VIDEO, MediaKind.AUDIO, MediaKind.TIMELINE),
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
            title="FFmpeg General Video workspace render",
            availability=OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE,
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; локальный General Video render доступен."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=(
                "general.workspace_revision",
                "general.ordered_visuals",
                "general.optional_soundtrack",
                "video.h264",
                "audio.aac",
                "media.project_owned",
            ),
        )
    )


def render_general_workspace(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _OFFER_ID or offer.capability_id != _CAPABILITY_ID:
        raise UnsupportedCapabilityExecution(
            f"General Video render requires exact offer {_OFFER_ID!r}"
        )
    allowed = {"workspace_revision_sha256"}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported video.render_general fields: {sorted(unknown)!r}"
        )
    revision = payload.get("workspace_revision_sha256")
    if not isinstance(revision, str) or len(revision) != 64:
        raise InvalidCapabilityInput("video.render_general requires workspace_revision_sha256")

    project = adapter.store.load_project(project_id)
    if compatibility_recipe_id(project) != _RECIPE_ID:
        raise InvalidCapabilityInput("video.render_general is available only for general_video")
    try:
        workspace = get_stage8_workspace(adapter.store, project_id)
    except Stage8WorkspaceError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    if workspace is None:
        raise InvalidCapabilityInput("General Video workspace is not saved")
    if workspace.revision_sha256 != revision:
        raise InvalidCapabilityInput("General Video workspace revision is stale")

    visual_bindings = tuple(item for item in workspace.sources if item.kind in {"image", "video"})
    audio_bindings = tuple(item for item in workspace.sources if item.kind == "audio")
    if not visual_bindings:
        raise InvalidCapabilityInput("General Video render requires at least one workspace image or video")
    if len(visual_bindings) > _MAX_VISUALS:
        raise InvalidCapabilityInput(f"General Video render supports at most {_MAX_VISUALS} visuals")
    if len(audio_bindings) > 1:
        raise InvalidCapabilityInput("General Video render supports at most one workspace audio track")

    source_media = ProjectSourceMediaStore(adapter.store)
    verified_visuals: list[tuple[Any, ProjectReference, Path]] = []
    verified_audio: tuple[Any, ProjectReference, Path] | None = None
    try:
        for binding in visual_bindings:
            reference, path = source_media.resolve_verified(
                project_id,
                binding.source_id,
                expected_kind=binding.kind,
            )
            if (
                reference.path != binding.path
                or reference.metadata.get("sha256") != binding.sha256
                or reference.metadata.get("size_bytes") != binding.size_bytes
            ):
                raise InvalidCapabilityInput("General Video visual binding is stale or corrupted")
            verified_visuals.append((binding, reference, path))
        if audio_bindings:
            binding = audio_bindings[0]
            reference, path = source_media.resolve_verified(
                project_id,
                binding.source_id,
                expected_kind="audio",
            )
            if (
                reference.path != binding.path
                or reference.metadata.get("sha256") != binding.sha256
                or reference.metadata.get("size_bytes") != binding.size_bytes
            ):
                raise InvalidCapabilityInput("General Video audio binding is stale or corrupted")
            verified_audio = (binding, reference, path)
    except SourceMediaError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc

    visual_specs: list[tuple[Any, ProjectReference, Path, int, bool]] = []
    for binding, reference, path in verified_visuals:
        if binding.kind == "image":
            visual_specs.append((binding, reference, path, _IMAGE_DURATION_US, False))
            continue
        probe = adapter._probe_path(canonical_path=reference.path, source=path)
        duration_us = probe.get("duration_us")
        if probe.get("has_video") is not True or not isinstance(duration_us, int) or duration_us <= 0:
            raise InvalidCapabilityInput(
                f"General Video source {reference.id!r} is not a video with known positive duration"
            )
        visual_specs.append(
            (binding, reference, path, duration_us, probe.get("has_audio") is True)
        )

    if verified_audio is not None:
        _binding, audio_reference, audio_path = verified_audio
        probe = adapter._probe_path(canonical_path=audio_reference.path, source=audio_path)
        if probe.get("has_audio") is not True:
            raise InvalidCapabilityInput("General Video workspace audio does not contain an audio stream")

    expected_duration_us = sum(item[3] for item in visual_specs)
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
        raise InvalidCapabilityInput("General Video render output path already exists")

    tasks_dir = adapter.store.project_directory(project_id) / "tasks"
    temp_paths: list[Path] = []
    manifest_path: Path | None = None
    try:
        segment_paths: list[Path] = []
        for _binding, _reference, source_path, duration_us, _has_audio in visual_specs:
            segment_path = tasks_dir / f"general-segment-{uuid.uuid4().hex}.mp4"
            temp_paths.append(segment_path)
            if _binding.kind == "image":
                command = [
                    adapter._tool("ffmpeg"),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-n",
                    "-loop",
                    "1",
                    "-i",
                    str(source_path),
                    "-t",
                    f"{duration_us}us",
                    "-vf",
                    _video_filter(),
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
            else:
                command = [
                    adapter._tool("ffmpeg"),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-n",
                    "-i",
                    str(source_path),
                    "-map",
                    "0:v:0",
                    "-t",
                    f"{duration_us}us",
                    "-vf",
                    _video_filter(),
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
            adapter._invoke(command, timeout=adapter.assemble_timeout_sec, tool="ffmpeg")
            if not segment_path.is_file() or segment_path.stat().st_size <= 0:
                raise CapabilityToolFailed("General Video normalized segment was not created")
            segment_paths.append(segment_path)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix="general-render-",
            suffix=".ffconcat",
            dir=tasks_dir,
            delete=False,
        ) as handle:
            manifest_path = Path(handle.name)
            handle.write("ffconcat version 1.0\n")
            for segment_path in segment_paths:
                handle.write(_concat_quote(segment_path))

        if verified_audio is None:
            visual_output = output_path
        else:
            visual_output = tasks_dir / f"general-visual-{uuid.uuid4().hex}.mp4"
            temp_paths.append(visual_output)

        concat_command = [
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
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(visual_output),
        ]
        adapter._invoke(concat_command, timeout=adapter.assemble_timeout_sec, tool="ffmpeg")
        if not visual_output.is_file() or visual_output.stat().st_size <= 0:
            raise CapabilityToolFailed("General Video visual master was not created")

        if verified_audio is not None:
            _binding, _audio_reference, audio_path = verified_audio
            mux_command = [
                adapter._tool("ffmpeg"),
                "-hide_banner",
                "-loglevel",
                "error",
                "-n",
                "-i",
                str(visual_output),
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                f"{expected_duration_us}us",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            adapter._invoke(mux_command, timeout=adapter.assemble_timeout_sec, tool="ffmpeg")

        if not output_path.is_file() or output_path.is_symlink() or output_path.stat().st_size <= 0:
            raise CapabilityToolFailed("General Video output is not a non-empty regular artifact")
        output_probe = adapter._probe_path(canonical_path=canonical_output, source=output_path)
        actual_duration_us = output_probe.get("duration_us")
        expected_audio = verified_audio is not None
        if (
            output_probe.get("has_video") is not True
            or output_probe.get("has_audio") is not expected_audio
            or not isinstance(actual_duration_us, int)
            or actual_duration_us <= 0
        ):
            raise CapabilityToolFailed("General Video output does not match expected media streams")
        tolerance_us = max(250_000, 3_000_000 // _OUTPUT_FPS)
        if abs(actual_duration_us - expected_duration_us) > tolerance_us:
            raise CapabilityToolFailed("General Video render duration does not match ordered visuals")

        visual_metadata = [
            {
                "source_id": reference.id,
                "kind": binding.kind,
                "path": reference.path,
                "sha256": reference.metadata.get("sha256"),
                "size_bytes": reference.metadata.get("size_bytes"),
                "duration_us": duration_us,
                "embedded_audio_ignored": has_audio,
            }
            for binding, reference, _path, duration_us, has_audio in visual_specs
        ]
        audio_metadata = None
        if verified_audio is not None:
            _binding, reference, _path = verified_audio
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
                "lifecycle": _LIFECYCLE,
                "composition_mode": _MODE,
                "workspace_revision_sha256": workspace.revision_sha256,
                "visual_bindings": visual_metadata,
                "audio_binding": audio_metadata,
                "image_duration_us": _IMAGE_DURATION_US,
                "expected_duration_us": expected_duration_us,
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
        for path in temp_paths:
            path.unlink(missing_ok=True)

    return CapabilityExecutionResult.from_offer(
        project_id=project_id,
        offer=offer,
        output={
            "path": canonical_output,
            "artifact_id": artifact_id,
            "workspace_revision_sha256": workspace.revision_sha256,
            "composition_mode": _MODE,
            "duration_us": actual_duration_us,
        },
        artifact=artifact.to_dict(),
    )
