"""Bounded local whisper.cpp execution for provider-neutral speech transcription."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from uv_studio.projects.dubbing import DubbingError, DubbingTranscript, TranscriptSegment
from uv_studio.projects.source_media import (
    ProjectSourceMediaStore,
    SourceMediaError,
    SourceMediaNotFound,
)
from uv_studio.projects.store import ProjectNotFound, ProjectStore, ProjectStoreError

from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import CapabilityOffer, CostClass, LocalityClass, OfferAvailability

RunCommand = Callable[..., subprocess.CompletedProcess[str]]
_MAX_TRANSCRIBE_SECONDS = 6 * 60 * 60
_MAX_SEGMENTS = 100_000
_DEFAULT_TIMEOUT_SEC = 6 * 60 * 60


def _run_command(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(*args, **kwargs)


def _require_int(value: Any, *, field_name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InvalidCapabilityInput(f"{field_name} must be an integer >= {minimum}")
    return value


def _language(value: Any) -> str:
    if value is None:
        return "auto"
    if not isinstance(value, str):
        raise InvalidCapabilityInput("language must be a string")
    normalized = value.strip().lower()
    if not normalized:
        raise InvalidCapabilityInput("language must not be empty")
    if normalized == "auto":
        return normalized
    parts = normalized.split("-")
    if not 2 <= len(parts[0]) <= 8 or not parts[0].isalpha():
        raise InvalidCapabilityInput("language must be 'auto' or a portable language tag")
    if any(not part or len(part) > 8 or not part.isalnum() for part in parts[1:]):
        raise InvalidCapabilityInput("language must be 'auto' or a portable language tag")
    return normalized


def _clean_segment_text(value: Any) -> str:
    if not isinstance(value, str):
        raise CapabilityToolFailed("whisper.cpp JSON segment text is not a string")
    normalized = value.strip()
    if not normalized:
        raise CapabilityToolFailed("whisper.cpp returned an empty transcription segment")
    return normalized


def _parse_offset_ms(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapabilityToolFailed(f"whisper.cpp JSON {field_name} offset is not numeric")
    parsed = int(value)
    if parsed < 0 or parsed != value:
        raise CapabilityToolFailed(f"whisper.cpp JSON {field_name} offset must be a non-negative integer")
    return parsed


class WhisperCppAdapter:
    """Execute one configured whisper.cpp runtime without exposing raw CLI control."""

    adapter_id = "local_whisper_cpp"

    def __init__(
        self,
        store: ProjectStore,
        *,
        runner: RunCommand = _run_command,
        binary_path: str | Path | None = None,
        model_path: str | Path | None = None,
        ffmpeg_path: str | Path | None = None,
        timeout_sec: int = _DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self.store = store
        self.source_media = ProjectSourceMediaStore(store)
        self.runner = runner
        self.binary_path = binary_path
        self.model_path = model_path
        self.ffmpeg_path = ffmpeg_path
        self.timeout_sec = timeout_sec

    @staticmethod
    def _validate_offer(offer: CapabilityOffer) -> None:
        if offer.adapter_id != WhisperCppAdapter.adapter_id:
            raise UnsupportedCapabilityExecution(
                f"whisper.cpp executor cannot run adapter {offer.adapter_id!r}"
            )
        if offer.capability_id != "speech.transcribe":
            raise UnsupportedCapabilityExecution(
                f"whisper.cpp executor does not implement {offer.capability_id!r}"
            )
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise UnsupportedCapabilityExecution(
                f"offer {offer.offer_id!r} is not currently available"
            )
        if offer.locality is not LocalityClass.LOCAL or offer.cost_class is not CostClass.FREE:
            raise UnsupportedCapabilityExecution(
                "whisper.cpp executor accepts only explicit local/free offers"
            )

    @staticmethod
    def _regular_runtime_file(value: str | Path | None, *, label: str) -> Path:
        if value is None:
            raise CapabilityToolUnavailable(f"{label} is not configured")
        candidate = Path(value).expanduser()
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise CapabilityToolUnavailable(f"{label} could not be resolved") from exc
        if not resolved.is_file():
            raise CapabilityToolUnavailable(f"{label} is not a regular file")
        return resolved

    def _binary(self) -> Path:
        configured = self.binary_path or os.environ.get("UV_WHISPER_CPP_BIN")
        if configured is not None:
            return self._regular_runtime_file(configured, label="whisper.cpp binary")
        discovered = shutil.which("whisper-cli")
        return self._regular_runtime_file(discovered, label="whisper.cpp binary")

    def _model(self) -> Path:
        configured = self.model_path or os.environ.get("UV_WHISPER_CPP_MODEL")
        return self._regular_runtime_file(configured, label="whisper.cpp model")

    def _ffmpeg(self) -> Path:
        configured = self.ffmpeg_path or shutil.which("ffmpeg")
        return self._regular_runtime_file(configured, label="ffmpeg")

    def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        self._validate_offer(offer)
        if not isinstance(payload, Mapping):
            raise InvalidCapabilityInput("speech.transcribe input must be a JSON object")
        allowed = {"source_id", "start_us", "end_us", "language"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(
                f"unsupported speech.transcribe fields: {sorted(unknown)!r}"
            )
        source_id = payload.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise InvalidCapabilityInput("speech.transcribe requires string field 'source_id'")
        source_id = source_id.strip()
        language = _language(payload.get("language"))

        try:
            source, source_path = self.source_media.resolve(project_id, source_id)
        except (ProjectNotFound, SourceMediaNotFound):
            raise
        except (SourceMediaError, ProjectStoreError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc

        if source.metadata.get("has_audio") is not True:
            raise InvalidCapabilityInput("speech.transcribe source is not registered with an audio stream")
        duration_us = source.metadata.get("duration_us")
        if isinstance(duration_us, bool) or not isinstance(duration_us, int) or duration_us <= 0:
            raise InvalidCapabilityInput("speech.transcribe source duration is unavailable")

        has_start = "start_us" in payload
        has_end = "end_us" in payload
        if has_start != has_end:
            raise InvalidCapabilityInput("start_us and end_us must be supplied together")
        if has_start:
            start_us = _require_int(payload.get("start_us"), field_name="start_us", minimum=0)
            end_us = _require_int(payload.get("end_us"), field_name="end_us", minimum=1)
        else:
            start_us = 0
            end_us = duration_us
        if end_us <= start_us:
            raise InvalidCapabilityInput("end_us must be greater than start_us")
        if end_us > duration_us:
            raise InvalidCapabilityInput("speech.transcribe range exceeds registered source duration")
        range_duration_us = end_us - start_us
        if range_duration_us > _MAX_TRANSCRIBE_SECONDS * 1_000_000:
            raise InvalidCapabilityInput(
                f"speech.transcribe supports at most {_MAX_TRANSCRIBE_SECONDS} seconds per execution"
            )

        binary = self._binary()
        model = self._model()
        ffmpeg = self._ffmpeg()
        tasks_dir = self.store.project_directory(project_id) / "tasks"

        with tempfile.TemporaryDirectory(prefix="whisper-cpp-", dir=tasks_dir) as tmp:
            tmp_path = Path(tmp)
            wav_path = tmp_path / "input.wav"
            output_prefix = tmp_path / "transcript"
            json_path = tmp_path / "transcript.json"

            self._invoke(
                [
                    str(ffmpeg),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(source_path),
                    "-ss",
                    f"{start_us}us",
                    "-t",
                    f"{range_duration_us}us",
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(wav_path),
                ],
                tool="ffmpeg",
            )
            if not wav_path.is_file() or wav_path.stat().st_size <= 44:
                raise CapabilityToolFailed("ffmpeg did not create a non-empty transcription WAV")

            whisper_command = [
                str(binary),
                "-m",
                str(model),
                "-f",
                str(wav_path),
                "-ojf",
                "-of",
                str(output_prefix),
                "-np",
                "-l",
                language,
            ]
            self._invoke(whisper_command, tool="whisper-cli")
            if not json_path.is_file() or json_path.stat().st_size == 0:
                raise CapabilityToolFailed("whisper.cpp did not produce the expected JSON output")
            try:
                raw = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CapabilityToolFailed("whisper.cpp returned malformed JSON output") from exc

        normalized = self._normalize_output(
            raw,
            source_id=source.id,
            source_sha256=source.metadata.get("sha256"),
            start_us=start_us,
            end_us=end_us,
        )
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output=normalized,
        )

    def _normalize_output(
        self,
        raw: Any,
        *,
        source_id: str,
        source_sha256: Any,
        start_us: int,
        end_us: int,
    ) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise CapabilityToolFailed("whisper.cpp JSON root must be an object")
        result = raw.get("result")
        detected_language = result.get("language") if isinstance(result, Mapping) else None
        if not isinstance(detected_language, str) or not detected_language.strip():
            raise CapabilityToolFailed("whisper.cpp JSON is missing result.language")
        transcription = raw.get("transcription")
        if not isinstance(transcription, list):
            raise CapabilityToolFailed("whisper.cpp JSON is missing transcription array")
        if len(transcription) > _MAX_SEGMENTS:
            raise CapabilityToolFailed("whisper.cpp returned too many transcription segments")

        segments: list[dict[str, Any]] = []
        previous_end = start_us
        for index, item in enumerate(transcription, start=1):
            if not isinstance(item, Mapping):
                raise CapabilityToolFailed("whisper.cpp transcription item must be an object")
            offsets = item.get("offsets")
            if not isinstance(offsets, Mapping):
                raise CapabilityToolFailed("whisper.cpp transcription item is missing offsets")
            from_ms = _parse_offset_ms(offsets.get("from"), field_name="from")
            to_ms = _parse_offset_ms(offsets.get("to"), field_name="to")
            segment_start = start_us + from_ms * 1_000
            segment_end = start_us + to_ms * 1_000
            if segment_end <= segment_start:
                raise CapabilityToolFailed("whisper.cpp returned a non-positive segment duration")
            if segment_start < start_us or segment_end > end_us + 20_000:
                raise CapabilityToolFailed("whisper.cpp segment offsets escaped the requested source range")
            segment_end = min(segment_end, end_us)
            if segment_start < previous_end:
                raise CapabilityToolFailed("whisper.cpp returned overlapping transcription segments")
            previous_end = segment_end
            segments.append(
                {
                    "segment_id": f"seg_{index:06d}",
                    "start_us": segment_start,
                    "end_us": segment_end,
                    "text": _clean_segment_text(item.get("text")),
                    "speaker_label": None,
                    "confidence": None,
                }
            )

        if not segments:
            raise CapabilityToolFailed("whisper.cpp returned no speech segments")
        if not isinstance(source_sha256, str) or len(source_sha256) != 64:
            raise InvalidCapabilityInput("registered source media is missing a valid sha256")

        try:
            transcript = DubbingTranscript(
                dubbing_id="asr_preview",
                source_id=source_id,
                source_sha256=source_sha256,
                language=detected_language,
                start_us=start_us,
                end_us=end_us,
                origin="asr",
                segments=tuple(TranscriptSegment.from_dict(item) for item in segments),
            )
        except DubbingError as exc:
            raise CapabilityToolFailed(f"normalized whisper.cpp output is invalid: {exc}") from exc

        return {
            "source_id": source_id,
            "source_sha256": source_sha256,
            "language": transcript.language,
            "start_us": start_us,
            "end_us": end_us,
            "segments": [item.to_dict() for item in transcript.segments],
        }

    def _invoke(self, command: list[str], *, tool: str) -> subprocess.CompletedProcess[str]:
        try:
            completed = self.runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CapabilityToolFailed(f"{tool} timed out") from exc
        except OSError as exc:
            raise CapabilityToolUnavailable(f"could not start {tool}: {exc}") from exc
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            if len(stderr) > 1200:
                stderr = stderr[-1200:]
            raise CapabilityToolFailed(
                f"{tool} failed with exit code {completed.returncode}: {stderr or 'no error output'}"
            )
        return completed
