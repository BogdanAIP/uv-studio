from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_musetalk_adapter,
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


class StubMuseTalkExecutor:
    adapter_id = "local_musetalk"

    def __init__(self) -> None:
        self.calls = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "artifact_id": "art_lipsync",
                "path": "artifacts/art_lipsync.mp4",
                "sha256": "2" * 64,
                "duration_us": 3_000_000,
                "engine": "musetalk_v15",
                "portrait_source_id": payload["portrait_source_id"],
                "speech_source_id": payload["speech_source_id"],
            },
        )


class MuseTalkExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="MuseTalk transport",
            recipe_id="performance_lip_sync",
        )
        self.registry = self._registry()
        self.executor = StubMuseTalkExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_musetalk_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = lambda: OneShotAuthorizationStore()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "video.digital_human",
            "Lip sync",
            "Local portrait + supplied speech lip-sync",
            OperationKind.GENERATION,
            (MediaKind.IMAGE, MediaKind.AUDIO),
            (MediaKind.VIDEO,),
            asynchronous=False,
        )
        adapter = AdapterDefinition(
            "local_musetalk",
            "MuseTalk 1.5",
            "Optional local MuseTalk runtime",
            AdapterKind.LOCAL,
        )
        registry = CapabilityRegistry((capability,), (adapter,))
        registry.register_offer(
            CapabilityOffer(
                "local_musetalk.video_digital_human",
                capability.capability_id,
                adapter.adapter_id,
                "Local MuseTalk lip-sync",
                OfferAvailability.AVAILABLE,
                "configured",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
            )
        )
        return registry

    def test_local_musetalk_dispatches_without_d017_authorization(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/video.digital_human/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {
                    "portrait_source_id": "src_portrait",
                    "speech_source_id": "src_speech",
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "local_musetalk.video_digital_human",
        )
        self.assertEqual(payload["result"]["adapter_id"], "local_musetalk")
        self.assertEqual(payload["result"]["output"]["engine"], "musetalk_v15")
        self.assertEqual(len(self.executor.calls), 1)

    def test_prepare_declares_local_free_without_remote_or_cost_consent(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/video.digital_human/prepare-execution",
            json={
                "selection_policy": "local_free_first",
                "input": {
                    "portrait_source_id": "src_portrait",
                    "speech_source_id": "src_speech",
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        authorization = response.json()["authorization"]
        self.assertFalse(authorization["authorization_required"])
        self.assertEqual(authorization["consent_required"], [])
        self.assertEqual(authorization["cost_estimate"]["state"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
