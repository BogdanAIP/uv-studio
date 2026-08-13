from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_argos_translate_adapter,
    get_execution_authorization_store,
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


class StubArgosExecutor:
    adapter_id = "local_argos_translate"

    def __init__(self) -> None:
        self.calls = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "source_language": "en",
                "target_language": "ru",
                "segments": [
                    {"segment_id": item["segment_id"], "text": f"RU:{item['text']}"}
                    for item in payload["segments"]
                ],
            },
        )


class ArgosTranslateExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Argos transport")
        self.registry = self._registry()
        self.executor = StubArgosExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_argos_translate_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = lambda: OneShotAuthorizationStore()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "text.translate",
            "Translate",
            "local segment-preserving translation",
            OperationKind.TRANSFORMATION,
            (MediaKind.TEXT,),
            (MediaKind.TEXT,),
        )
        adapter = AdapterDefinition(
            "local_argos_translate",
            "Argos Translate",
            "optional local translation runtime",
            AdapterKind.LOCAL,
        )
        registry = CapabilityRegistry((capability,), (adapter,))
        registry.register_offer(
            CapabilityOffer(
                "local_argos_translate.text_translate",
                capability.capability_id,
                adapter.adapter_id,
                "Local translation",
                OfferAvailability.AVAILABLE,
                "configured",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
                ("text.translate", "text.segment_preservation"),
            )
        )
        return registry

    def test_local_translation_dispatches_without_d017_and_preserves_segment_ids(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/text.translate/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {
                    "source_language": "en",
                    "target_language": "ru",
                    "segments": [
                        {"segment_id": "seg_1", "text": "Hello"},
                        {"segment_id": "seg_2", "text": "World"},
                    ],
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "local_argos_translate.text_translate",
        )
        self.assertEqual(payload["result"]["adapter_id"], "local_argos_translate")
        self.assertEqual(
            [item["segment_id"] for item in payload["result"]["output"]["segments"]],
            ["seg_1", "seg_2"],
        )
        self.assertEqual(len(self.executor.calls), 1)

    def test_prepare_reports_local_free_without_remote_or_cost_consent(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/text.translate/prepare-execution",
            json={
                "selection_policy": "local_free_first",
                "input": {
                    "source_language": "en",
                    "target_language": "ru",
                    "segments": [{"segment_id": "seg_1", "text": "Hello"}],
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
