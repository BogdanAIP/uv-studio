from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.adapters.whisperx_alignment import (
    WhisperXAlignmentAdapter,
    register_whisperx_alignment_adapter,
)
from uv_studio.capabilities.execution import CapabilityToolFailed
from uv_studio.projects.prepared_speech import PreparedSpeechTake
from uv_studio.projects.store import ProjectStore


class _PreparedState:
    def __init__(self, take) -> None:
        self.take = take

    def get(self, take_id):
        return self.take


class _PreparedFacade:
    def __init__(self, take) -> None:
        self.take = take

    def validate_project(self, project_id):
        return _PreparedState(self.take)


class _DubbingState:
    def __init__(self) -> None:
        self.transcript = SimpleNamespace(
            dubbing_id="dub_1",
            language="en-US",
            segments=(SimpleNamespace(segment_id="seg_1", text="Hello world"),),
        )

    def get_transcript(self, dubbing_id):
        return self.transcript


class _DubbingFacade:
    def validate_project(self, project_id):
        return _DubbingState()


class _AudioFacade:
    def __init__(self, audio_path: Path) -> None:
        self.audio_path = audio_path

    def resolve(self, project_id, audio_id):
        return SimpleNamespace(metadata={"sha256": "2" * 64}, path="assets/aud_1.wav"), self.audio_path


class WhisperXAlignmentAdapterTests(unittest.TestCase):
    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "audio.align",
            "Align",
            "Forced alignment",
            OperationKind.UNDERSTANDING,
            (MediaKind.AUDIO, MediaKind.TEXT),
            (MediaKind.TEXT,),
        )
        registry = CapabilityRegistry(
            (capability,),
            (
                AdapterDefinition(
                    "placeholder",
                    "Placeholder",
                    "constructor placeholder",
                    AdapterKind.LOCAL,
                ),
            ),
        )
        return registry

    @staticmethod
    def _offer() -> CapabilityOffer:
        return CapabilityOffer(
            "local_whisperx_alignment.audio_align",
            "audio.align",
            "local_whisperx_alignment",
            "WhisperX offline alignment",
            OfferAvailability.AVAILABLE,
            "configured",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    def test_offer_is_configuration_required_without_runtime_or_local_model_dir(self) -> None:
        registry = self._registry()
        with (
            mock.patch(
                "uv_studio.capabilities.adapters.whisperx_alignment._runtime_installed",
                return_value=True,
            ),
            mock.patch(
                "uv_studio.capabilities.adapters.whisperx_alignment._configured_model_dir",
                return_value=None,
            ),
        ):
            register_whisperx_alignment_adapter(registry)
        offer = registry.offers_for("audio.align")[0]
        self.assertEqual(offer.availability, OfferAvailability.CONFIGURATION_REQUIRED)
        self.assertIn("runtime.no_hidden_model_download", offer.features)
        self.assertEqual(offer.locality, LocalityClass.LOCAL)
        self.assertEqual(offer.cost_class, CostClass.FREE)

    def test_fake_runtime_produces_reviewable_word_alignment_draft_from_take_id_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_store = ProjectStore(root / "projects")
            project = project_store.create_project(title="WhisperX")
            audio_path = root / "voice.wav"
            audio_path.write_bytes(b"fake-audio")
            model_dir = root / "models"
            model_dir.mkdir()
            take = PreparedSpeechTake(
                take_id="take_1",
                dubbing_id="dub_1",
                script_kind="transcript",
                script_id="dub_1",
                script_sha256="1" * 64,
                audio_id="aud_1",
                audio_sha256="2" * 64,
                duration_us=2_000_000,
                origin="recorded",
                segment_id="seg_1",
            )
            calls = []

            def runtime(text, language, path, duration_us, model_name, configured_model_dir):
                calls.append((text, language, path, duration_us, model_name, configured_model_dir))
                return [
                    {"word": "Hello", "start": 0.10, "end": 0.65, "score": 0.94},
                    {"word": "world", "start": 0.70, "end": 1.40, "score": 0.91},
                ]

            adapter = WhisperXAlignmentAdapter(
                project_store,
                align_runtime=runtime,
                model_dir=model_dir,
            )
            adapter.prepared_speech = _PreparedFacade(take)
            adapter.dubbing = _DubbingFacade()
            adapter.audio = _AudioFacade(audio_path)
            result = adapter.execute(
                project_id=project.project_id,
                offer=self._offer(),
                payload={"take_id": "take_1"},
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "Hello world")
            self.assertEqual(calls[0][1], "en")
            self.assertEqual(result.output["take_id"], "take_1")
            self.assertEqual(
                result.output["marks"],
                [
                    {
                        "mark_id": "mark_000001",
                        "unit": "word",
                        "text": "Hello",
                        "audio_start_us": 100_000,
                        "audio_end_us": 650_000,
                        "confidence": 0.94,
                    },
                    {
                        "mark_id": "mark_000002",
                        "unit": "word",
                        "text": "world",
                        "audio_start_us": 700_000,
                        "audio_end_us": 1_400_000,
                        "confidence": 0.91,
                    },
                ],
            )

    def test_incomplete_or_out_of_range_word_alignment_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ProjectStore(root / "projects")
            project = store.create_project(title="WhisperX bad")
            model_dir = root / "models"
            model_dir.mkdir()
            audio_path = root / "voice.wav"
            audio_path.write_bytes(b"fake")
            take = PreparedSpeechTake(
                take_id="take_1",
                dubbing_id="dub_1",
                script_kind="transcript",
                script_id="dub_1",
                script_sha256="1" * 64,
                audio_id="aud_1",
                audio_sha256="2" * 64,
                duration_us=1_000_000,
                origin="recorded",
                segment_id="seg_1",
            )
            adapter = WhisperXAlignmentAdapter(
                store,
                align_runtime=lambda *args: [
                    {"word": "Hello", "start": 0.8, "end": 1.2, "score": 0.9}
                ],
                model_dir=model_dir,
            )
            adapter.prepared_speech = _PreparedFacade(take)
            adapter.dubbing = _DubbingFacade()
            adapter.audio = _AudioFacade(audio_path)
            with self.assertRaisesRegex(CapabilityToolFailed, "outside the prepared speech duration"):
                adapter.execute(
                    project_id=project.project_id,
                    offer=self._offer(),
                    payload={"take_id": "take_1"},
                )


if __name__ == "__main__":
    unittest.main()
