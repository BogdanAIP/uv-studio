from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_whisperx_alignment_adapter,
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


class StubWhisperXExecutor:
    adapter_id = "local_whisperx_alignment"

    def __init__(self) -> None:
        self.calls = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "take_id": payload["take_id"],
                "language": "en",
                "marks": [
                    {
                        "mark_id": "mark_000001",
                        "unit": "word",
                        "text": "Hello",
                        "audio_start_us": 100_000,
                        "audio_end_us": 650_000,
                        "confidence": 0.94,
                    }
                ],
            },
        )


class WhisperXAlignmentExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="WhisperX transport")
        self.registry = self._registry()
        self.executor = StubWhisperXExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_whisperx_alignment_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = lambda: OneShotAuthorizationStore()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "audio.align",
            "Align",
            "offline forced alignment",
            OperationKind.UNDERSTANDING,
            (MediaKind.AUDIO, MediaKind.TEXT),
            (MediaKind.TEXT,),
        )
        adapter = AdapterDefinition(
            "local_whisperx_alignment",
            "WhisperX alignment",
            "optional local forced alignment runtime",
            AdapterKind.LOCAL,
        )
        registry = CapabilityRegistry((capability,), (adapter,))
        registry.register_offer(
            CapabilityOffer(
                "local_whisperx_alignment.audio_align",
                capability.capability_id,
                adapter.adapter_id,
                "WhisperX offline alignment",
                OfferAvailability.AVAILABLE,
                "configured",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
                ("audio.forced_alignment", "audio.word_timestamps"),
            )
        )
        return registry

    def test_local_alignment_dispatches_without_d017_and_keeps_server_bounded_input(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/audio.align/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {"take_id": "take_1"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "local_whisperx_alignment.audio_align",
        )
        self.assertEqual(payload["result"]["adapter_id"], "local_whisperx_alignment")
        self.assertEqual(payload["result"]["output"]["take_id"], "take_1")
        self.assertEqual(len(self.executor.calls), 1)
        self.assertEqual(self.executor.calls[0][2], {"take_id": "take_1"})

    def test_prepare_reports_local_free_no_consent(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/audio.align/prepare-execution",
            json={"selection_policy": "local_free_first", "input": {"take_id": "take_1"}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        authorization = response.json()["authorization"]
        self.assertFalse(authorization["authorization_required"])
        self.assertEqual(authorization["consent_required"], [])
        self.assertEqual(authorization["cost_estimate"]["state"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
