from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_whisper_cpp_adapter,
)
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityExecutionResult,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class StubWhisperExecutor:
    adapter_id = "local_whisper_cpp"

    def __init__(self) -> None:
        self.calls = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "source_id": payload["source_id"],
                "source_sha256": "1" * 64,
                "language": "en",
                "start_us": 0,
                "end_us": 1_000_000,
                "segments": [
                    {
                        "segment_id": "seg_000001",
                        "start_us": 0,
                        "end_us": 1_000_000,
                        "text": "Hello",
                        "speaker_label": None,
                        "confidence": None,
                    }
                ],
            },
        )


class WhisperCppExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(recipe_id="general_video", title="Whisper transport")
        self.registry = self._registry()
        self.executor = StubWhisperExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_whisper_cpp_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = lambda: OneShotAuthorizationStore()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "speech.transcribe",
            "Transcribe",
            "local speech transcription",
            OperationKind.SPEECH,
            (MediaKind.VIDEO, MediaKind.AUDIO),
            (MediaKind.TEXT, MediaKind.METADATA),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            "local_whisper_cpp",
            "whisper.cpp",
            "local whisper runtime",
            AdapterKind.LOCAL,
        )
        registry = CapabilityRegistry((capability,), (adapter,))
        registry.register_offer(
            CapabilityOffer(
                "local_whisper_cpp.speech_transcribe",
                capability.capability_id,
                adapter.adapter_id,
                "Local transcription",
                OfferAvailability.AVAILABLE,
                "configured",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
            )
        )
        return registry

    def test_local_transcription_dispatches_without_d017_authorization(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/speech.transcribe/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {"source_id": "src_video", "language": "auto"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "local_whisper_cpp.speech_transcribe",
        )
        self.assertEqual(payload["result"]["adapter_id"], "local_whisper_cpp")
        self.assertEqual(payload["result"]["output"]["segments"][0]["text"], "Hello")
        self.assertEqual(len(self.executor.calls), 1)

    def test_prepare_declares_no_remote_or_cost_consent(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/speech.transcribe/prepare-execution",
            json={
                "selection_policy": "local_free_first",
                "input": {"source_id": "src_video"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        authorization = response.json()["authorization"]
        self.assertFalse(authorization["authorization_required"])
        self.assertEqual(authorization["consent_required"], [])
        self.assertEqual(authorization["cost_estimate"]["state"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
