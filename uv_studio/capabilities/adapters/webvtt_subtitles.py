"""Deterministic provider-neutral WebVTT export from current dubbing state."""

from __future__ import annotations

import hashlib
import html
import os
import re
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from uv_studio.projects.dubbing import DubbingError, DubbingStore
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.prepared_speech import canonical_revision_sha256
from uv_studio.projects.root_staging import (
    acquire_webvtt_root_staging,
    release_root_staging,
)
from uv_studio.projects.store import ProjectStore, ProjectStoreError
from uv_studio.projects.task_records import ProjectTaskRecordStore

from ..execution import (
    CapabilityExecutionResult,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from ..registry import CapabilityRegistry

_ADAPTER_ID = "local_webvtt"
_CAPABILITY_ID = "subtitle.export_webvtt"
_OFFER_ID = "local_webvtt.subtitle_export"
_BLANK_LINE_RE = re.compile(r"^[\t ]*$")


def register_webvtt_subtitle_adapter(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _CAPABILITY_ID,
            "Экспорт WebVTT",
            "Детерминированный WebVTT из текущего transcript или его точной translation revision.",
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.TEXT, MediaKind.TIMELINE),
            (MediaKind.SUBTITLE,),
            asynchronous=False,
        )
    )
    registry.register_adapter(
        AdapterDefinition(
            _ADAPTER_ID,
            "UV Studio WebVTT exporter",
            "Локальная проекция канонического текста/таймкодов без внешнего движка.",
            AdapterKind.LOCAL,
        )
    )
    registry.register_offer(
        CapabilityOffer(
            _OFFER_ID,
            _CAPABILITY_ID,
            _ADAPTER_ID,
            "Canonical WebVTT export",
            OfferAvailability.AVAILABLE,
            "Встроенный локальный детерминированный экспорт доступен без настройки.",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
            ("subtitle.webvtt", "timeline.exact_source_binding"),
        )
    )


def _timestamp(value_us: int) -> str:
    if value_us < 0:
        raise InvalidCapabilityInput("subtitle timestamp must be non-negative")
    millis = value_us // 1000
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _cue_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    normalized = "\n".join(
        line for line in normalized.split("\n") if not _BLANK_LINE_RE.fullmatch(line)
    )
    return html.escape(normalized, quote=False)


def _render_webvtt(segments: tuple[tuple[str, int, int, str], ...]) -> str:
    lines = ["WEBVTT", ""]
    previous_start = -1
    for segment_id, start_us, end_us, text in segments:
        if start_us < 0 or end_us <= start_us:
            raise InvalidCapabilityInput("subtitle cue range must be non-negative and forward")
        if start_us < previous_start:
            raise InvalidCapabilityInput(
                "subtitle cues must be ordered by non-decreasing start time"
            )
        start_ms = start_us // 1000
        end_ms = (end_us + 999) // 1000
        if end_ms <= start_ms:
            end_ms = start_ms + 1
        lines.extend(
            [
                segment_id,
                f"{_timestamp(start_ms * 1000)} --> {_timestamp(end_ms * 1000)}",
                _cue_text(text),
                "",
            ]
        )
        previous_start = start_us
    return "\n".join(lines)


class WebVTTSubtitleAdapter:
    adapter_id = _ADAPTER_ID

    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.dubbing = DubbingStore(store)

    @staticmethod
    def _validate_offer(offer: CapabilityOffer) -> None:
        if offer.adapter_id != _ADAPTER_ID or offer.capability_id != _CAPABILITY_ID:
            raise UnsupportedCapabilityExecution("WebVTT executor received an incompatible offer")
        if offer.offer_id != _OFFER_ID or offer.availability is not OfferAvailability.AVAILABLE:
            raise UnsupportedCapabilityExecution("WebVTT offer is not executable")

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        self._validate_offer(offer)
        unknown = set(payload).difference({"dubbing_id", "translation_id"})
        if unknown:
            raise InvalidCapabilityInput(f"unsupported subtitle export fields: {sorted(unknown)!r}")
        dubbing_id = payload.get("dubbing_id")
        translation_id = payload.get("translation_id")
        if not isinstance(dubbing_id, str) or not dubbing_id.strip():
            raise InvalidCapabilityInput("subtitle export requires non-empty dubbing_id")
        if translation_id is not None and (
            not isinstance(translation_id, str) or not translation_id.strip()
        ):
            raise InvalidCapabilityInput("translation_id must be null or a non-empty string")
        try:
            state = self.dubbing.validate_project(project_id)
            transcript = state.get_transcript(dubbing_id.strip())
            transcript_sha = canonical_revision_sha256(transcript.to_dict())
            if translation_id is None:
                script_kind = "transcript"
                script_id = transcript.dubbing_id
                script_sha = transcript_sha
                language = transcript.language
                text_by_id = {item.segment_id: item.text for item in transcript.segments}
            else:
                translation = state.get_translation(translation_id.strip())
                if translation.dubbing_id != transcript.dubbing_id:
                    raise InvalidCapabilityInput(
                        "translation_id belongs to a different dubbing transcript"
                    )
                script_kind = "translation"
                script_id = translation.translation_id
                script_sha = canonical_revision_sha256(translation.to_dict())
                language = translation.target_language
                text_by_id = {item.segment_id: item.text for item in translation.segments}
            segments = tuple(
                sorted(
                    (
                        (item.segment_id, item.start_us, item.end_us, text_by_id[item.segment_id])
                        for item in transcript.segments
                    ),
                    key=lambda item: (item[1], item[2], item[0]),
                )
            )
        except InvalidCapabilityInput:
            raise
        except (DubbingError, ProjectStoreError, KeyError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc

        webvtt = _render_webvtt(segments)
        encoded = webvtt.encode("utf-8")
        artifact_id = f"sub_{uuid.uuid4().hex}"
        relative_path = f"artifacts/{artifact_id}.vtt"
        output: Path | None = None
        staged_output: Path | None = None
        try:
            output = self.store.resolve_project_file(
                project_id,
                relative_path,
                must_exist=False,
                allowed_roots=("artifacts",),
            )
            if output.exists() or output.is_symlink():
                raise InvalidCapabilityInput("subtitle export refuses to overwrite an existing artifact")

            staged_output = acquire_webvtt_root_staging(self.store.root, artifact_id)
            with staged_output.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())

            artifact = ProjectReference(
                id=artifact_id,
                kind="subtitle",
                path=relative_path,
                metadata={
                    "capability_id": offer.capability_id,
                    "offer_id": offer.offer_id,
                    "format": "webvtt",
                    "content_type": "text/vtt; charset=utf-8",
                    "dubbing_id": transcript.dubbing_id,
                    "source_id": transcript.source_id,
                    "source_sha256": transcript.source_sha256,
                    "transcript_sha256": transcript_sha,
                    "script_kind": script_kind,
                    "script_id": script_id,
                    "script_sha256": script_sha,
                    "language": language,
                    "cue_count": len(segments),
                    "sha256": hashlib.sha256(encoded).hexdigest(),
                    "size_bytes": len(encoded),
                    "timing_precision": "webvtt_millisecond_from_canonical_microseconds",
                    "lifecycle": "subtitle_export",
                },
            )

            with ProjectTaskRecordStore(self.store).project_lock(project_id):
                fenced_output = self.store.resolve_project_file(
                    project_id,
                    relative_path,
                    must_exist=False,
                    allowed_roots=("artifacts",),
                )
                if fenced_output.exists() or fenced_output.is_symlink():
                    raise InvalidCapabilityInput(
                        "subtitle export refuses to overwrite an existing artifact"
                    )

                final_written = False
                try:
                    os.replace(staged_output, fenced_output)
                    final_written = True
                    project = self.store.load_project(project_id)
                    self.store.update_project(
                        project_id,
                        artifacts=(*project.artifacts, artifact),
                    )
                except Exception:
                    if final_written:
                        try:
                            current = self.store.load_project(project_id)
                            registered = any(item.id == artifact_id for item in current.artifacts)
                        except Exception:
                            registered = True
                        if not registered:
                            fenced_output.unlink(missing_ok=True)
                    raise

        finally:
            if staged_output is not None:
                release_root_staging(staged_output)

        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "path": relative_path,
                "artifact_id": artifact.id,
                "format": "webvtt",
                "language": language,
                "cue_count": len(segments),
                "script_kind": script_kind,
                "script_id": script_id,
            },
            artifact=artifact.to_dict(),
        )
