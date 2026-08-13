"""Deterministic browser-compatible preview projection for a registered video artifact."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectNotFound, ProjectStoreError

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

_PREVIEW_CAPABILITY_ID = "video.preview_artifact"
_PREVIEW_OFFER_ID = "local_ffmpeg.video_preview_artifact"
_PREVIEW_OUTPUT_ROOTS = ("artifacts",)
_PREVIEW_MODE = "authoritative_artifact_to_h264_aac_mp4"


def register_artifact_preview_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _PREVIEW_CAPABILITY_ID,
            "Браузерный предпросмотр видеоартефакта",
            (
                "Детерминированная browser-compatible MP4-проекция уже зарегистрированного "
                "project-owned видеоартефакта без повторного монтажа timeline."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.VIDEO,),
            (MediaKind.VIDEO,),
            asynchronous=False,
        )
    )
    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    registry.register_offer(
        CapabilityOffer(
            offer_id=_PREVIEW_OFFER_ID,
            capability_id=_PREVIEW_CAPABILITY_ID,
            adapter_id="local_ffmpeg",
            title="FFmpeg H.264/AAC browser preview",
            availability=(OfferAvailability.UNAVAILABLE if missing else OfferAvailability.AVAILABLE),
            reason=(
                f"Не найдены обязательные локальные инструменты: {', '.join(missing)}."
                if missing
                else "FFmpeg и FFprobe найдены в PATH; browser preview доступен локально."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=("video.preview", "video.mp4", "video.project_owned_artifact"),
        )
    )


def create_artifact_preview(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _PREVIEW_OFFER_ID:
        raise UnsupportedCapabilityExecution(
            f"artifact preview requires exact offer {_PREVIEW_OFFER_ID!r}"
        )
    allowed = {"artifact_id"}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported video.preview_artifact fields: {sorted(unknown)!r}"
        )
    artifact_id = payload.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise InvalidCapabilityInput("video.preview_artifact requires non-empty string artifact_id")
    artifact_id = artifact_id.strip()

    try:
        project = adapter.store.load_project(project_id)
    except ProjectNotFound:
        raise
    source_reference = next(
        (item for item in project.artifacts if item.id == artifact_id and item.kind == "video"),
        None,
    )
    if source_reference is None:
        raise InvalidCapabilityInput("video.preview_artifact source artifact was not found")
    try:
        source = adapter.store.resolve_project_file(
            project_id,
            source_reference.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    if not source.is_file() or source.is_symlink():
        raise InvalidCapabilityInput("video.preview_artifact source must be a regular project artifact")

    source_probe = adapter._probe_path(canonical_path=source_reference.path, source=source)
    streams = source_probe.get("streams")
    if not isinstance(streams, list):
        streams = []
    video_streams = [
        item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"
    ]
    audio_streams = [
        item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"
    ]
    if len(video_streams) != 1:
        raise InvalidCapabilityInput(
            "video.preview_artifact currently requires exactly one video stream"
        )
    if len(audio_streams) > 1:
        raise InvalidCapabilityInput(
            "video.preview_artifact currently supports at most one audio stream"
        )

    preview_id = f"art_{uuid.uuid4().hex}"
    canonical_output = f"artifacts/{preview_id}.mp4"
    try:
        output_path = adapter.store.resolve_project_file(
            project_id,
            canonical_output,
            must_exist=False,
            allowed_roots=_PREVIEW_OUTPUT_ROOTS,
        )
    except (ProjectValidationError, ProjectStoreError) as exc:
        raise InvalidCapabilityInput(str(exc)) from exc
    if output_path.exists() or output_path.is_symlink():
        raise InvalidCapabilityInput(
            f"video.preview_artifact refuses to overwrite existing output: {canonical_output!r}"
        )

    command = [
        adapter._tool("ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-i",
        str(source),
        "-map",
        "0:v:0",
    ]
    if audio_streams:
        command.extend(["-map", "0:a:0"])
    command.extend(
        [
            "-sn",
            "-dn",
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
    if audio_streams:
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    command.append(str(output_path))

    try:
        adapter._invoke(command, timeout=adapter.extract_timeout_sec, tool="ffmpeg")
        try:
            validated = adapter.store.resolve_project_file(
                project_id,
                canonical_output,
                must_exist=True,
                allowed_roots=_PREVIEW_OUTPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise CapabilityToolFailed(
                "browser preview output escaped its project artifact boundary"
            ) from exc
        if validated != output_path or validated.is_symlink() or not validated.is_file():
            raise CapabilityToolFailed("browser preview output is not a regular project artifact")
        if validated.stat().st_size <= 0:
            raise CapabilityToolFailed("browser preview output is empty")

        output_probe = adapter._probe_path(canonical_path=canonical_output, source=validated)
        output_streams = output_probe.get("streams")
        if not isinstance(output_streams, list):
            output_streams = []
        output_video = [
            item
            for item in output_streams
            if isinstance(item, dict) and item.get("codec_type") == "video"
        ]
        output_audio = [
            item
            for item in output_streams
            if isinstance(item, dict) and item.get("codec_type") == "audio"
        ]
        if len(output_video) != 1 or output_video[0].get("codec_name") != "h264":
            raise CapabilityToolFailed("browser preview output is not a single H.264 video stream")
        if len(output_audio) != len(audio_streams):
            raise CapabilityToolFailed("browser preview audio presence does not match source artifact")
        if output_audio and output_audio[0].get("codec_name") != "aac":
            raise CapabilityToolFailed("browser preview audio stream is not AAC")
        format_name = output_probe.get("format_name")
        if not isinstance(format_name, str) or "mp4" not in format_name.split(","):
            raise CapabilityToolFailed("browser preview output is not an MP4 container")

        metadata: dict[str, Any] = {
            "capability_id": offer.capability_id,
            "offer_id": offer.offer_id,
            "source_artifact_id": source_reference.id,
            "source_artifact_path": source_reference.path,
            "preview_mode": _PREVIEW_MODE,
            "lifecycle": "browser_preview",
            "content_type": "video/mp4",
        }
        source_path = source_reference.metadata.get("source_path")
        if isinstance(source_path, str):
            metadata["source_path"] = source_path
        edit_ids = source_reference.metadata.get("edit_ids")
        if isinstance(edit_ids, list) and all(isinstance(item, str) for item in edit_ids):
            metadata["edit_ids"] = list(edit_ids)

        preview_reference = ProjectReference(
            id=preview_id,
            kind="video",
            path=canonical_output,
            metadata=metadata,
        )
        refreshed = adapter.store.load_project(project_id)
        adapter.store.update_project(
            project_id,
            artifacts=(*refreshed.artifacts, preview_reference),
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise

    return CapabilityExecutionResult.from_offer(
        project_id=project_id,
        offer=offer,
        output={
            "path": canonical_output,
            "source_artifact_id": source_reference.id,
            "preview_mode": _PREVIEW_MODE,
        },
        artifact=preview_reference.to_dict(),
    )
