from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.external_execution import get_execution_authorization_store
from uv_studio.api.mcp import get_mcp_manager
from uv_studio.api.projects import get_project_store
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
from uv_studio.capabilities.consent import ExecutionAuthorizationStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class FakeMCPManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def resolve_offer_binding(self, offer):
        tool = "cloud_generate" if offer.offer_id.endswith("cloud") else "echo_metadata"
        return SimpleNamespace(profile_id="fixture"), SimpleNamespace(tool_name=tool)

    async def invoke_offer(self, offer, arguments, **kwargs):
        self.calls.append((offer.offer_id, dict(arguments)))
        _, binding = self.resolve_offer_binding(offer)
        return binding, {
            "content": [{"type": "text", "text": "fixture-result"}],
            "structuredContent": {"offer": offer.offer_id, "input": dict(arguments)},
            "isError": False,
        }


class ExternalExecutionConsentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Consent API")
        self.registry = self._registry()
        self.manager = FakeMCPManager()
        self.grants = ExecutionAuthorizationStore(ttl_seconds=60)
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_mcp_manager] = lambda: self.manager
        app.dependency_overrides[get_execution_authorization_store] = lambda: self.grants
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capabilities = (
            CapabilityDefinition(
                "media.understand",
                "Understand",
                "understand media",
                OperationKind.UNDERSTANDING,
                (MediaKind.TEXT,),
                (MediaKind.TEXT,),
                asynchronous=True,
            ),
            CapabilityDefinition(
                "video.generate",
                "Generate video",
                "generate video",
                OperationKind.GENERATION,
                (MediaKind.TEXT,),
                (MediaKind.VIDEO,),
                asynchronous=True,
            ),
        )
        adapter = AdapterDefinition("mcp.fixture", "Fixture", "fixture", AdapterKind.MCP)
        registry = CapabilityRegistry(capabilities, (adapter,))
        registry.register_offer(
            CapabilityOffer(
                "mcp.fixture.echo",
                "media.understand",
                "mcp.fixture",
                "Remote free echo",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.REMOTE,
                CostClass.FREE,
                True,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "mcp.fixture.cloud",
                "video.generate",
                "mcp.fixture",
                "Paid-capable cloud fixture",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.REMOTE,
                CostClass.POTENTIALLY_PAID,
                True,
            )
        )
        return registry

    def _base(self, capability: str) -> str:
        return f"/api/uv/projects/{self.project.project_id}/capabilities/{capability}"

    def test_prepare_paid_capability_reports_unknown_cost_and_required_consent(self) -> None:
        response = self.client.post(
            self._base("video.generate") + "/prepare-execution",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.cloud",
                "input": {"prompt": "test"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        prepared = response.json()["prepared"]
        self.assertTrue(prepared["authorization_required"])
        self.assertTrue(prepared["remote_consent_required"])
        self.assertTrue(prepared["cost_consent_required"])
        self.assertTrue(prepared["unknown_cost_ack_required"])
        self.assertEqual(prepared["intent"]["cost_estimate"]["state"], "unknown")
        self.assertIsNone(prepared["intent"]["cost_estimate"]["amount"])

    def test_authorize_unknown_cost_requires_explicit_acknowledgement(self) -> None:
        response = self.client.post(
            self._base("video.generate") + "/authorize-execution",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.cloud",
                "input": {"prompt": "test"},
                "confirm_remote": True,
                "confirm_cost": True,
                "acknowledge_unknown_cost": False,
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "consent_required")
        self.assertEqual(len(self.manager.calls), 0)

    def _authorize_cloud(self, payload=None) -> str:
        input_payload = payload or {"prompt": "test"}
        response = self.client.post(
            self._base("video.generate") + "/authorize-execution",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.cloud",
                "input": input_payload,
                "confirm_remote": True,
                "confirm_cost": True,
                "acknowledge_unknown_cost": True,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["authorization"]["authorization_token"]

    def test_one_shot_authorization_executes_exact_intent_and_records_secret_free_run(self) -> None:
        token = self._authorize_cloud()
        response = self.client.post(
            self._base("video.generate") + "/execute",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.cloud",
                "input": {"prompt": "test"},
                "authorization_token": token,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(self.manager.calls), 1)
        self.assertEqual(payload["external_run"]["status"], "succeeded")
        run_id = payload["external_run"]["run_id"]
        stored = self.client.get(
            f"/api/uv/projects/{self.project.project_id}/external-runs/{run_id}"
        )
        self.assertEqual(stored.status_code, 200, stored.text)
        encoded = json.dumps(stored.json())
        self.assertNotIn(token, encoded)
        self.assertNotIn("authorization_token", encoded)
        self.assertEqual(stored.json()["authorization_mode"], "one_shot")
        self.assertEqual(stored.json()["cost_estimate"]["state"], "unknown")

    def test_authorization_cannot_be_replayed(self) -> None:
        token = self._authorize_cloud()
        body = {
            "selection_policy": "pinned_offer",
            "offer_id": "mcp.fixture.cloud",
            "input": {"prompt": "test"},
            "authorization_token": token,
        }
        self.assertEqual(self.client.post(self._base("video.generate") + "/execute", json=body).status_code, 200)
        replay = self.client.post(self._base("video.generate") + "/execute", json=body)
        self.assertEqual(replay.status_code, 409, replay.text)
        self.assertEqual(replay.json()["detail"]["code"], "authorization_rejected")
        self.assertEqual(len(self.manager.calls), 1)

    def test_changed_input_rejects_grant_before_mcp_invocation(self) -> None:
        token = self._authorize_cloud({"prompt": "approved"})
        response = self.client.post(
            self._base("video.generate") + "/execute",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.cloud",
                "input": {"prompt": "changed"},
                "authorization_token": token,
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "authorization_rejected")
        self.assertEqual(len(self.manager.calls), 0)

    def test_missing_authorization_returns_consent_required_without_invocation(self) -> None:
        response = self.client.post(
            self._base("video.generate") + "/execute",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.cloud",
                "input": {"prompt": "test"},
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "consent_required")
        self.assertEqual(len(self.manager.calls), 0)

    def test_remote_free_requires_remote_authorization_but_not_cost_confirmation(self) -> None:
        auth = self.client.post(
            self._base("media.understand") + "/authorize-execution",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.echo",
                "input": {"text": "hi"},
                "confirm_remote": True,
            },
        )
        self.assertEqual(auth.status_code, 200, auth.text)
        prepared = auth.json()["prepared"]
        self.assertTrue(prepared["remote_consent_required"])
        self.assertFalse(prepared["cost_consent_required"])
        token = auth.json()["authorization"]["authorization_token"]
        executed = self.client.post(
            self._base("media.understand") + "/execute",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.echo",
                "input": {"text": "hi"},
                "authorization_token": token,
            },
        )
        self.assertEqual(executed.status_code, 200, executed.text)

    def test_unregistered_raw_tool_name_cannot_be_invoked(self) -> None:
        response = self.client.post(
            self._base("video.generate") + "/execute",
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.unbound_raw_tool",
                "input": {},
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(len(self.manager.calls), 0)


if __name__ == "__main__":
    unittest.main()
