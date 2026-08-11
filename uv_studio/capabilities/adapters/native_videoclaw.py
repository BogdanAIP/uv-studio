"""Narrow native VideoClaw compatibility execution.

This adapter intentionally does not expose arbitrary vendored functions. The first
and only executable operation in this slice is the already-advertised
``native_videoclaw.edge_tts`` offer, implemented against the same Edge TTS contract
as the pinned VideoClaw source.
"""

from __future__ import annotations

import importlib
import math
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import ProjectStore, ProjectStoreError
from uv_studio.projects.task_records import ProjectTaskRecordStore

from ..authorization import ExecutionPreparation
from ..execution import (
    CapabilityExecutionResult,
    CapabilityToolFailed,
    CapabilityToolUnavailable,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from ..models import CapabilityOffer, CostClass, LocalityClass, OfferAvailability
from ..provenance import ExternalExecutionTarget, ExternalRunProvenance

CommunicateFactory = Callable[..., Any]

_EDGE_TTS_OFFER_ID = "native_videoclaw.edge_tts"
_EDGE_TTS_CAPABILITY_ID = "speech.synthesize"
_DEFAULT_VOICE = "zh-CN-YunjianNeural"
_MAX_TEXT_CHARS = 20_000
_MAX_VOICE_CHARS = 128
_OUTPUT_ROOTS = ("artifacts",)


def _speed_to_rate(speed: float) -> str:
    """Match the pinned VideoClaw ``speed_to_rate`` conversion exactly."""

    percent = int(round((speed - 1.0) * 100))
    sign = "+" if percent >= 0 else ""
    return f"{sign}{percent}%"


class NativeVideoClawAdapter:
    adapter_id = "native_videoclaw"

    def __init__(
        self,
        store: ProjectStore,
        *,
        communicate_factory: CommunicateFactory | None = None,
    ) -> None:
        self.store = store
        self._injected_communicate_factory = communicate_factory
        self.provenance = ExternalRunProvenance(ProjectTaskRecordStore(store))

    @staticmethod
    def _validate_offer(offer: CapabilityOffer) -> None:
        if offer.adapter_id != NativeVideoClawAdapter.adapter_id:
            raise UnsupportedCapabilityExecution(
                f"native VideoClaw executor cannot run adapter {offer.adapter_id!r}"
            )
        if offer.offer_id != _EDGE_TTS_OFFER_ID or offer.capability_id != _EDGE_TTS_CAPABILITY_ID:
            raise UnsupportedCapabilityExecution(
                f"native VideoClaw executor does not implement offer {offer.offer_id!r}"
            )
        if offer.availability is not OfferAvailability.AVAILABLE:
            raise UnsupportedCapabilityExecution(
                f"offer {offer.offer_id!r} is not currently available"
            )
        if offer.locality is not LocalityClass.REMOTE or offer.cost_class is not CostClass.FREE:
            raise UnsupportedCapabilityExecution(
                "Edge TTS compatibility requires the catalogued remote/free offer semantics"
            )

    def _communicate_factory(self) -> CommunicateFactory:
        if self._injected_communicate_factory is not None:
            return self._injected_communicate_factory
        try:
            edge_tts = importlib.import_module("edge_tts")
        except Exception as exc:
            raise CapabilityToolUnavailable(
                "edge-tts could not be loaded in this installation"
            ) from exc
        factory = getattr(edge_tts, "Communicate", None)
        if not callable(factory):
            raise CapabilityToolUnavailable("edge-tts Communicate is unavailable")
        return factory

    @staticmethod
    def _validate_payload(payload: Mapping[str, Any]) -> tuple[str, str, float]:
        allowed = {"text", "voice", "speed"}
        unknown = set(payload).difference(allowed)
        if unknown:
            raise InvalidCapabilityInput(
                f"unsupported speech.synthesize fields: {sorted(unknown)!r}"
            )

        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise InvalidCapabilityInput("speech.synthesize requires non-empty string field 'text'")
        if len(text) > _MAX_TEXT_CHARS:
            raise InvalidCapabilityInput(
                f"speech.synthesize text exceeds {_MAX_TEXT_CHARS} characters"
            )

        voice = payload.get("voice", _DEFAULT_VOICE)
        if not isinstance(voice, str) or not voice.strip():
            raise InvalidCapabilityInput("speech.synthesize voice must be a non-empty string")
        voice = voice.strip()
        if len(voice) > _MAX_VOICE_CHARS:
            raise InvalidCapabilityInput(
                f"speech.synthesize voice exceeds {_MAX_VOICE_CHARS} characters"
            )

        speed_value = payload.get("speed", 1.0)
        if isinstance(speed_value, bool):
            raise InvalidCapabilityInput("speech.synthesize speed must be a positive finite number")
        try:
            speed = float(speed_value)
        except (TypeError, ValueError) as exc:
            raise InvalidCapabilityInput(
                "speech.synthesize speed must be a positive finite number"
            ) from exc
        if not math.isfinite(speed) or speed <= 0:
            raise InvalidCapabilityInput(
                "speech.synthesize speed must be a positive finite number"
            )
        return text, voice, speed

    async def execute(
        self,
        *,
        project_id: str,
        offer: CapabilityOffer,
        preparation: ExecutionPreparation,
        payload: Mapping[str, Any],
    ) -> CapabilityExecutionResult:
        self._validate_offer(offer)
        if not isinstance(payload, Mapping):
            raise InvalidCapabilityInput("capability input must be a JSON object")
        text, voice, speed = self._validate_payload(payload)
        communicate_factory = self._communicate_factory()

        artifact_id = f"art_{uuid.uuid4().hex}"
        canonical_output = f"artifacts/{artifact_id}.mp3"
        try:
            output_path = self.store.resolve_project_file(
                project_id,
                canonical_output,
                must_exist=False,
                allowed_roots=_OUTPUT_ROOTS,
            )
        except (ProjectValidationError, ProjectStoreError) as exc:
            raise InvalidCapabilityInput(str(exc)) from exc
        if output_path.exists() or output_path.is_symlink():
            raise InvalidCapabilityInput(
                f"speech.synthesize refuses to overwrite existing output: {canonical_output!r}"
            )

        record = self.provenance.start(
            project_id=project_id,
            offer=offer,
            preparation=preparation,
            target=ExternalExecutionTarget(
                profile_id=self.adapter_id,
                tool_name="edge_tts",
            ),
        )
        artifact_registered = False
        try:
            try:
                communicate = communicate_factory(
                    text=text,
                    voice=voice,
                    rate=_speed_to_rate(speed),
                )
                save = getattr(communicate, "save", None)
                if not callable(save):
                    raise CapabilityToolUnavailable("edge-tts Communicate.save is unavailable")
                await save(str(output_path))
            except CapabilityToolUnavailable:
                raise
            except Exception as exc:
                raise CapabilityToolFailed("edge-tts synthesis failed") from exc

            try:
                output_size = output_path.stat().st_size if output_path.is_file() else 0
            except OSError as exc:
                raise CapabilityToolFailed("edge-tts output could not be validated") from exc
            if output_size <= 0:
                raise CapabilityToolFailed(
                    "edge-tts reported success but output file is empty or missing"
                )

            artifact = ProjectReference(
                id=artifact_id,
                kind="audio",
                path=canonical_output,
                metadata={
                    "capability_id": offer.capability_id,
                    "offer_id": offer.offer_id,
                    "voice": voice,
                    "speed": speed,
                },
            )
            project = self.store.load_project(project_id)
            self.store.update_project(
                project_id,
                artifacts=(*project.artifacts, artifact),
            )
            artifact_registered = True

            portable_result = {
                "path": canonical_output,
                "voice": voice,
                "speed": speed,
            }
            self.provenance.succeed(record, portable_result)
            return CapabilityExecutionResult.from_offer(
                project_id=project_id,
                offer=offer,
                output={"run_id": record.run_id, **portable_result},
                artifact=artifact.to_dict(),
            )
        except Exception as exc:
            if not artifact_registered:
                output_path.unlink(missing_ok=True)
            self.provenance.fail(record, exc)
            raise
