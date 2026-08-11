"""Exact UV Studio-owned compatibility adapters for pinned VideoClaw behavior.

This module intentionally does not expose arbitrary vendor modules/functions.
Only explicitly supported native offer IDs can execute.
"""

from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore

from ..authorization import ExecutionPreparation
from ..execution import CapabilityExecutionResult
from ..models import CapabilityOffer
from ..provenance import ExternalExecutorIdentity, ExternalRunProvenance

EDGE_TTS_OFFER_ID = "native_videoclaw.edge_tts"
EDGE_TTS_CAPABILITY_ID = "speech.synthesize"
EDGE_TTS_DEFAULT_VOICE = "zh-CN-YunjianNeural"
EDGE_TTS_MAX_TEXT_CHARS = 20_000
EDGE_TTS_MAX_VOICE_CHARS = 128
EDGE_TTS_MIN_SPEED = 0.5
EDGE_TTS_MAX_SPEED = 2.0
EDGE_TTS_MAX_OUTPUT_BYTES = 100 * 1024 * 1024


class NativeVideoClawExecutionError(RuntimeError):
    code = "native_videoclaw_execution_failed"


class NativeVideoClawInputRejected(NativeVideoClawExecutionError):
    code = "native_videoclaw_invalid_input"


class NativeVideoClawDependencyUnavailable(NativeVideoClawExecutionError):
    code = "native_videoclaw_dependency_unavailable"


class NativeVideoClawRemoteFailed(NativeVideoClawExecutionError):
    code = "native_videoclaw_remote_failed"


class NativeVideoClawOutputInvalid(NativeVideoClawExecutionError):
    code = "native_videoclaw_output_invalid"


class EdgeTTSRuntime(Protocol):
    def available(self) -> bool: ...

    async def save(self, *, text: str, voice: str, rate: str, output_path: Path) -> None: ...


class InstalledEdgeTTSRuntime:
    """Narrow compatibility with pinned VideoClaw's edge-tts 7.2.7 usage."""

    def available(self) -> bool:
        return importlib.util.find_spec("edge_tts") is not None

    async def save(self, *, text: str, voice: str, rate: str, output_path: Path) -> None:
        try:
            import edge_tts
        except ImportError as exc:  # pragma: no cover - guarded by available(), retained for races
            raise NativeVideoClawDependencyUnavailable(
                "edge-tts is not installed in the current UV Studio Python environment"
            ) from exc
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            await communicate.save(str(output_path))
        except Exception as exc:
            raise NativeVideoClawRemoteFailed(
                "Edge TTS remote synthesis failed"
            ) from exc


class NativeVideoClawAdapter:
    adapter_id = "native_videoclaw"

    def __init__(
        self,
        project_store: ProjectStore,
        *,
        edge_tts_runtime: EdgeTTSRuntime | None = None,
    ) -> None:
        self.project_store = project_store
        self.edge_tts_runtime = edge_tts_runtime or InstalledEdgeTTSRuntime()
        self.provenance = ExternalRunProvenance(ProjectTaskRecordStore(project_store))

    async def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        preparation: ExecutionPreparation,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        if offer.adapter_id != self.adapter_id:
            raise NativeVideoClawExecutionError("selected offer is not a native VideoClaw offer")
        if offer.offer_id != EDGE_TTS_OFFER_ID:
            raise NativeVideoClawExecutionError(
                f"native offer {offer.offer_id!r} has no exact compatibility executor"
            )
        if offer.capability_id != EDGE_TTS_CAPABILITY_ID:
            raise NativeVideoClawExecutionError("Edge TTS offer capability does not match speech.synthesize")

        request = self._parse_edge_tts_input(payload)
        if not self.edge_tts_runtime.available():
            raise NativeVideoClawDependencyUnavailable(
                "edge-tts is not installed in the current UV Studio Python environment"
            )

        record = self.provenance.start(
            project_id=project_id,
            offer=offer,
            preparation=preparation,
            executor=ExternalExecutorIdentity.for_native_videoclaw("edge_tts"),
        )
        relative_output = f"artifacts/{record.run_id}.mp3"
        output_path = self.project_store.resolve_project_file(
            project_id,
            relative_output,
            allowed_roots=("artifacts",),
        )
        try:
            await self.edge_tts_runtime.save(
                text=request["text"],
                voice=request["voice"],
                rate=request["rate"],
                output_path=output_path,
            )
            summary = self._validate_output(output_path)
        except Exception as exc:
            output_path.unlink(missing_ok=True)
            wrapped = exc if isinstance(exc, NativeVideoClawExecutionError) else NativeVideoClawRemoteFailed(
                "Edge TTS remote synthesis failed"
            )
            self.provenance.fail(record, wrapped)
            raise wrapped from exc if wrapped is not exc else None

        result_payload = {
            "artifact": relative_output,
            "bytes": summary["bytes"],
            "sha256": summary["sha256"],
            "voice": request["voice"],
            "speed": request["speed"],
        }
        self.provenance.succeed(
            record,
            result_payload,
            references={"artifact": relative_output},
        )
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"run_id": record.run_id, **result_payload},
        )

    @classmethod
    def _parse_edge_tts_input(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise NativeVideoClawInputRejected("Edge TTS input must be a JSON object")
        allowed = {"text", "voice", "speed"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise NativeVideoClawInputRejected(
                f"unsupported Edge TTS input fields: {sorted(unknown)!r}"
            )
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise NativeVideoClawInputRejected("text must be a non-empty string")
        if len(text) > EDGE_TTS_MAX_TEXT_CHARS:
            raise NativeVideoClawInputRejected(
                f"text exceeds UV Studio limit of {EDGE_TTS_MAX_TEXT_CHARS} characters"
            )
        voice = payload.get("voice", EDGE_TTS_DEFAULT_VOICE)
        if not isinstance(voice, str) or not voice.strip():
            raise NativeVideoClawInputRejected("voice must be a non-empty string")
        voice = voice.strip()
        if len(voice) > EDGE_TTS_MAX_VOICE_CHARS or any(ch.isspace() for ch in voice):
            raise NativeVideoClawInputRejected("voice is not a valid bounded Edge TTS voice identifier")
        speed_raw = payload.get("speed", 1.0)
        if isinstance(speed_raw, bool):
            raise NativeVideoClawInputRejected("speed must be numeric")
        try:
            speed = float(speed_raw)
        except (TypeError, ValueError) as exc:
            raise NativeVideoClawInputRejected("speed must be numeric") from exc
        if not EDGE_TTS_MIN_SPEED <= speed <= EDGE_TTS_MAX_SPEED:
            raise NativeVideoClawInputRejected(
                f"speed must be between {EDGE_TTS_MIN_SPEED} and {EDGE_TTS_MAX_SPEED}"
            )
        return {
            "text": text,
            "voice": voice,
            "speed": speed,
            "rate": cls._speed_to_rate(speed),
        }

    @staticmethod
    def _speed_to_rate(speed: float) -> str:
        percent = int(round((speed - 1.0) * 100))
        sign = "+" if percent >= 0 else ""
        return f"{sign}{percent}%"

    @staticmethod
    def _validate_output(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise NativeVideoClawOutputInvalid("Edge TTS completed without an output file")
        size = path.stat().st_size
        if size <= 0:
            raise NativeVideoClawOutputInvalid("Edge TTS produced an empty output file")
        if size > EDGE_TTS_MAX_OUTPUT_BYTES:
            raise NativeVideoClawOutputInvalid(
                f"Edge TTS output exceeds {EDGE_TTS_MAX_OUTPUT_BYTES} bytes"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"bytes": size, "sha256": digest}
