"""Optional offline WhisperX forced alignment for exact prepared speech takes."""

from __future__ import annotations

import importlib
import importlib.util
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from uv_studio.projects.dubbing import DubbingError, DubbingStore, DubbingTranslationNotFound
from uv_studio.projects.prepared_audio import PreparedAudioError, ProjectPreparedAudioStore
from uv_studio.projects.prepared_speech import PreparedSpeechError, PreparedSpeechStore
from uv_studio.projects.store import ProjectStore, ProjectStoreError

from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from ..registry import CapabilityRegistry

_WHISPERX_ADAPTER_ID = "local_whisperx_alignment"
_WHISPERX_OFFER_ID = "local_whisperx_alignment.audio_align"
_MODEL_DIR_ENV = "UV_STUDIO_WHISPERX_MODEL_DIR"
_DEVICE_ENV = "UV_STUDIO_WHISPERX_DEVICE"
_MODEL_ENV = "UV_STUDIO_WHISPERX_ALIGN_MODEL"
_MAX_MARK_TEXT_LENGTH = 512

AlignRuntime = Callable[
    [str, str, Path, int, str | None, Path],
    list[dict[str, Any]],
]


def _runtime_installed() -> bool:
    try:
        return importlib.util.find_spec("whisperx") is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _configured_model_dir() -> Path | None:
    value = os.getenv(_MODEL_DIR_ENV)
    if not value or not value.strip():
        return None
    try:
        path = Path(value).expanduser().resolve()
    except OSError:
        return None
    return path if path.is_dir() else None


def register_whisperx_alignment_adapter(registry: CapabilityRegistry) -> None:
    registry.register_adapter(
        AdapterDefinition(
            adapter_id=_WHISPERX_ADAPTER_ID,
            title="WhisperX forced alignment runtime",
            description=(
                "Опциональный BSD-2-Clause precision-layer для word-level forced alignment. "
                "Torch/pyannote/transformers и alignment models не входят в core UV Studio."
            ),
            kind=AdapterKind.LOCAL,
        )
    )
    installed = _runtime_installed()
    model_dir = _configured_model_dir()
    available = installed and model_dir is not None
    if not installed:
        reason = "Установите optional WhisperX runtime для точного forced alignment."
    elif model_dir is None:
        reason = (
            f"WhisperX runtime найден, но {_MODEL_DIR_ENV} не указывает на локальный каталог моделей; "
            "скрытая загрузка моделей отключена."
        )
    else:
        reason = (
            "WhisperX runtime и локальный model directory настроены; конкретная языковая модель "
            "проверяется при выполнении без сетевой загрузки."
        )
    registry.register_offer(
        CapabilityOffer(
            offer_id=_WHISPERX_OFFER_ID,
            capability_id="audio.align",
            adapter_id=_WHISPERX_ADAPTER_ID,
            title="WhisperX offline forced alignment",
            availability=(OfferAvailability.AVAILABLE if available else OfferAvailability.CONFIGURATION_REQUIRED),
            reason=reason,
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=(
                "audio.forced_alignment",
                "audio.word_timestamps",
                "runtime.optional",
                "runtime.no_hidden_model_download",
            ),
        )
    )


def _language_code(value: str) -> str:
    normalized = value.strip().lower().split("-", 1)[0]
    if not 2 <= len(normalized) <= 8 or not normalized.isalpha():
        raise InvalidCapabilityInput("prepared speech language is not supported as a portable language code")
    return normalized


def _default_align_runtime(
    text: str,
    language: str,
    audio_path: Path,
    duration_us: int,
    model_name: str | None,
    model_dir: Path,
) -> list[dict[str, Any]]:
    try:
        module = importlib.import_module("whisperx.alignment")
        load_align_model = module.load_align_model
        align = module.align
    except (ImportError, AttributeError, OSError) as exc:
        raise CapabilityToolUnavailable("WhisperX alignment runtime is not installed correctly") from exc

    device = (os.getenv(_DEVICE_ENV) or "cpu").strip() or "cpu"
    try:
        model, metadata = load_align_model(
            language_code=language,
            device=device,
            model_name=model_name,
            model_dir=str(model_dir),
            model_cache_only=True,
        )
        result = align(
            transcript=[{"start": 0.0, "end": duration_us / 1_000_000, "text": text}],
            model=model,
            align_model_metadata=metadata,
            audio=str(audio_path),
            device=device,
            return_char_alignments=False,
            print_progress=False,
        )
    except Exception as exc:
        raise CapabilityToolFailed(
            "WhisperX forced alignment failed using the configured offline model cache: "
            f"{exc}"
        ) from exc
    words = result.get("word_segments") if isinstance(result, Mapping) else None
    if not isinstance(words, list):
        raise CapabilityToolFailed("WhisperX returned no word_segments alignment output")
    return words


class WhisperXAlignmentAdapter:
    """Produce a reviewable alignment draft; canonical persistence is a separate Command API action."""

    adapter_id = _WHISPERX_ADAPTER_ID

    def __init__(
        self,
        store: ProjectStore,
        *,
        align_runtime: AlignRuntime = _default_align_runtime,
        model_dir: Path | None = None,
        model_name: str | None = None,
    ) -> None:
        self.store = store
        self.prepared_speech = PreparedSpeechStore(store)
        self.dubbing = DubbingStore(store)
        self.audio = ProjectPreparedAudioStore(store)
        self.align_runtime = align_runtime
        self.model_dir = model_dir or _configured_model_dir()
        self.model_name = model_name if model_name is not None else (os.getenv(_MODEL_ENV) or None)

    @staticmethod
    def _validate_offer(offer: CapabilityOffer) -> None:
        if offer.adapter_id != WhisperXAlignmentAdapter.adapter_id:
            raise UnsupportedCapabilityExecution(
                f"WhisperX executor cannot run adapter {offer.adapter_id!r}"
            )
        if offer.capability_id != "audio.align":
            raise UnsupportedCapabilityExecution(
                f"WhisperX executor does not implement {offer.capability_id!r}"
            )
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise UnsupportedCapabilityExecution(
                f"offer {offer.offer_id!r} is not currently available"
            )
        if offer.locality is not LocalityClass.LOCAL or offer.cost_class is not CostClass.FREE:
            raise UnsupportedCapabilityExecution(
                "WhisperX executor accepts only explicit local/free offers"
            )

    def _script(self, project_id: str, take) -> tuple[str, str]:
        try:
            dubbing = self.dubbing.validate_project(project_id)
            transcript = dubbing.get_transcript(take.dubbing_id)
        except DubbingError as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        if take.script_kind == "translation":
            try:
                translation = dubbing.get_translation(take.script_id)
            except DubbingTranslationNotFound as exc:
                raise InvalidCapabilityInput(str(exc)) from exc
            language = translation.target_language
            by_id = {item.segment_id: item.text for item in translation.segments}
        else:
            language = transcript.language
            by_id = {item.segment_id: item.text for item in transcript.segments}
        if take.segment_id is not None:
            text = by_id.get(take.segment_id)
            if text is None:
                raise InvalidCapabilityInput("prepared speech segment is missing from the current script")
        else:
            text = " ".join(
                by_id[item.segment_id]
                for item in transcript.segments
                if item.segment_id in by_id
            )
        if not text.strip():
            raise InvalidCapabilityInput("prepared speech script contains no alignable text")
        return text.strip(), _language_code(language)

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        self._validate_offer(offer)
        if not isinstance(payload, Mapping):
            raise InvalidCapabilityInput("audio.align input must be a JSON object")
        unknown = set(payload).difference({"take_id"})
        if unknown:
            raise InvalidCapabilityInput(f"unsupported audio.align fields: {sorted(unknown)!r}")
        take_id = payload.get("take_id")
        if not isinstance(take_id, str) or not take_id.strip():
            raise InvalidCapabilityInput("audio.align requires non-empty string field 'take_id'")
        if self.model_dir is None or not self.model_dir.is_dir():
            raise CapabilityToolUnavailable(
                f"{_MODEL_DIR_ENV} must point to a local WhisperX alignment model cache"
            )
        try:
            take = self.prepared_speech.validate_project(project_id).get(take_id.strip())
            audio_ref, audio_path = self.audio.resolve(project_id, take.audio_id)
        except (PreparedSpeechError, PreparedAudioError, ProjectStoreError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        if audio_ref.metadata.get("sha256") != take.audio_sha256:
            raise InvalidCapabilityInput("prepared speech audio revision changed before alignment")
        text, language = self._script(project_id, take)
        words = self.align_runtime(
            text,
            language,
            audio_path,
            take.duration_us,
            self.model_name,
            self.model_dir,
        )
        if not words:
            raise CapabilityToolFailed("WhisperX returned an empty forced alignment")

        marks: list[dict[str, Any]] = []
        for index, word in enumerate(words, start=1):
            if not isinstance(word, Mapping):
                raise CapabilityToolFailed("WhisperX word alignment entry is not an object")
            raw_text = word.get("word")
            start = word.get("start")
            end = word.get("end")
            score = word.get("score")
            if not isinstance(raw_text, str) or not raw_text.strip() or len(raw_text.strip()) > _MAX_MARK_TEXT_LENGTH:
                raise CapabilityToolFailed("WhisperX returned invalid aligned word text")
            if isinstance(start, bool) or not isinstance(start, (int, float)):
                raise CapabilityToolFailed(f"WhisperX word {raw_text!r} has no usable start timestamp")
            if isinstance(end, bool) or not isinstance(end, (int, float)):
                raise CapabilityToolFailed(f"WhisperX word {raw_text!r} has no usable end timestamp")
            start_us = round(float(start) * 1_000_000)
            end_us = round(float(end) * 1_000_000)
            if start_us < 0 or end_us <= start_us or end_us > take.duration_us:
                raise CapabilityToolFailed(
                    f"WhisperX word {raw_text!r} is outside the prepared speech duration"
                )
            confidence = None
            if score is not None:
                if isinstance(score, bool) or not isinstance(score, (int, float)):
                    raise CapabilityToolFailed(f"WhisperX word {raw_text!r} has invalid score")
                confidence = float(score)
                if not 0.0 <= confidence <= 1.0:
                    raise CapabilityToolFailed(f"WhisperX word {raw_text!r} score is outside 0..1")
            marks.append(
                {
                    "mark_id": f"mark_{index:06d}",
                    "unit": "word",
                    "text": raw_text.strip(),
                    "audio_start_us": start_us,
                    "audio_end_us": end_us,
                    "confidence": confidence,
                }
            )

        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "take_id": take.take_id,
                "language": language,
                "marks": marks,
            },
        )
