"""Deterministic prepared-audio loudness measurement through FFmpeg loudnorm analysis."""

from __future__ import annotations

import json
import math
import shutil
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from uv_studio.projects.prepared_audio import (
    PreparedAudioError,
    PreparedAudioNotFound,
    ProjectPreparedAudioStore,
)

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

_AUDIO_LOUDNESS_CAPABILITY_ID = "audio.measure_loudness"
_AUDIO_LOUDNESS_OFFER_ID = "local_ffmpeg.audio_measure_loudness"


def register_audio_loudness_capability(registry: CapabilityRegistry) -> None:
    registry.register_capability(
        CapabilityDefinition(
            _AUDIO_LOUDNESS_CAPABILITY_ID,
            "Измерение громкости речи",
            (
                "Детерминированное измерение integrated loudness, true peak и loudness range "
                "подготовленной аудиодорожки без изменения файла."
            ),
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.AUDIO,),
            (MediaKind.METADATA,),
            asynchronous=False,
        )
    )
    ffmpeg = shutil.which("ffmpeg")
    registry.register_offer(
        CapabilityOffer(
            offer_id=_AUDIO_LOUDNESS_OFFER_ID,
            capability_id=_AUDIO_LOUDNESS_CAPABILITY_ID,
            adapter_id="local_ffmpeg",
            title="FFmpeg loudnorm measurement",
            availability=(
                OfferAvailability.AVAILABLE if ffmpeg else OfferAvailability.UNAVAILABLE
            ),
            reason=(
                "FFmpeg найден в PATH; локальное измерение громкости доступно."
                if ffmpeg
                else "FFmpeg не найден в PATH; локальное измерение громкости недоступно."
            ),
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=("audio.lufs", "audio.true_peak", "audio.lra"),
        )
    )


def _parse_metric(value: Any) -> float | None:
    if value in (None, "", "-inf", "inf", "+inf", "nan", "NaN"):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CapabilityToolFailed("FFmpeg loudnorm returned a non-numeric metric") from exc
    return parsed if math.isfinite(parsed) else None


def _analysis_json(stderr: str) -> dict[str, Any]:
    end = stderr.rfind("}")
    start = stderr.rfind("{", 0, end + 1)
    if start < 0 or end <= start:
        raise CapabilityToolFailed("FFmpeg loudnorm did not return JSON measurement output")
    try:
        payload = json.loads(stderr[start : end + 1])
    except json.JSONDecodeError as exc:
        raise CapabilityToolFailed("FFmpeg loudnorm returned malformed JSON measurement output") from exc
    if not isinstance(payload, dict):
        raise CapabilityToolFailed("FFmpeg loudnorm measurement output must be an object")
    return payload


def measure_prepared_audio_loudness(
    adapter: "LocalFFmpegRangeAdapter",
    *,
    project_id: str,
    offer: CapabilityOffer,
    payload: Mapping[str, Any],
) -> CapabilityExecutionResult:
    if offer.offer_id != _AUDIO_LOUDNESS_OFFER_ID:
        raise UnsupportedCapabilityExecution(
            f"audio loudness measurement requires exact offer {_AUDIO_LOUDNESS_OFFER_ID!r}"
        )
    allowed = {"audio_id"}
    unknown = set(payload).difference(allowed)
    if unknown:
        raise InvalidCapabilityInput(
            f"unsupported audio.measure_loudness fields: {sorted(unknown)!r}"
        )
    audio_id = payload.get("audio_id")
    if not isinstance(audio_id, str) or not audio_id.strip():
        raise InvalidCapabilityInput("audio.measure_loudness requires string field 'audio_id'")
    audio_id = audio_id.strip()
    try:
        reference, path = ProjectPreparedAudioStore(adapter.store).resolve(project_id, audio_id)
    except PreparedAudioNotFound as exc:
        raise InvalidCapabilityInput(f"prepared audio {audio_id!r} is not registered") from exc
    except PreparedAudioError as exc:
        raise InvalidCapabilityInput(str(exc)) from exc

    command = [
        adapter._tool("ffmpeg"),
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-af",
        "loudnorm=I=-23:LRA=7:TP=-2:print_format=json",
        "-f",
        "null",
        "-",
    ]
    completed = adapter._invoke(
        command,
        timeout=adapter.extract_timeout_sec,
        tool="ffmpeg",
    )
    analysis = _analysis_json(completed.stderr or "")
    integrated = _parse_metric(analysis.get("input_i"))
    true_peak = _parse_metric(analysis.get("input_tp"))
    lra = _parse_metric(analysis.get("input_lra"))
    threshold = _parse_metric(analysis.get("input_thresh"))

    output = {
        "audio_id": reference.id,
        "audio_sha256": reference.metadata.get("sha256"),
        "duration_us": reference.metadata.get("duration_us"),
        "measurable": integrated is not None and true_peak is not None,
        "integrated_lufs": integrated,
        "true_peak_dbtp": true_peak,
        "loudness_range_lu": lra,
        "threshold_lufs": threshold,
    }
    return CapabilityExecutionResult.from_offer(
        project_id=project_id,
        offer=offer,
        output=output,
    )
