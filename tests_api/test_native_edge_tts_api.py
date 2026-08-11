from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
    get_mcp_execution_adapter,
    get_native_videoclaw_adapter,
)
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities.adapters.native_videoclaw import NativeVideoClawAdapter
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.capabilities.models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class FakeEdgeTTSRuntime:
    def __init__(self, *, available: bool = True, fail: bool = False) -> None:
        self._available = available
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def available(self) -> bool:
        return self._available

    async def save(self, *, text, voice, rate, output_path) -> None:
        self.calls.append({"text": text, "voice": voice, "rate": rate})
        if self.fail:
            raise RuntimeError("raw-provider-body-must-not-persist")
        Path(output_path).write_bytes(b"ID3native-api-test")


class NativeEdgeTTSApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Native Edge TTS API")
        self.registry = self._registry()
        self.runtime = FakeEdgeTTSRuntime()
        self.native = NativeVideoClawAdapter(self.store, edge_tts_runtime=self.runtime)
        self.authorizations = OneShotAuthorizationStore()

        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_native_videoclaw_adapter] = lambda: self.native
        app.dependency_overrides[get_execution_authorization_store] = lambda: self.authorizations
        app.dependency_overrides[get_mcp_execution_adapter] = lambda: None
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: None
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            capability_id="speech.synthesize",
            title="Speech synthesis",
            description="Synthesize speech from text.",
            operation=OperationKind.SYNTHESIS,
            input_kinds=(MediaKind.TEXT,),
            output_kinds=(MediaKind.AUDIO,),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            adapter_id="native_videoclaw",
            title="Native VideoClaw compatibility",
            description="Exact pinned compatibility operations.",
            kind=AdapterKind.NATIVE,
        )
        registry = CapabilityRegistry((capability,), (adapter,))
        registry.register_offer(
            CapabilityOffer(
                offer_id="native_videoclaw.edge_tts",
                capability_id="speech.synthesize",
                adapter_id="native_videoclaw",
                title="Edge TTS",
                availability=OfferAvailability.AVAILABLE,
                reason="test runtime",
                locality=LocalityClass.REMOTE,
                cost_class=CostClass.FREE,
                asynchronous=True,
                features=("speech.tts",),
            )
        )
        return registry

    def _url(self, action: str = "execute") -> str:
        return (
            f"/api/uv/projects/{self.project.project_id}"
            f"/capabilities/speech.synthesize/{action}"
        )

    def _body(self, *, text: str = "Hello") -> dict:
        return {
            "selection_policy": "pinned_offer",
            "offer_id": "native_videoclaw.edge_tts",
            "input": {"text": text, "voice": "en-US-GuyNeural", "speed": 1.0},
        }

    def _records(self) -> list[dict]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(
                (self.store.project_directory(self.project.project_id) / "tasks").glob("run_*.json")
            )
        ]

    def test_remote_free_offer_requires_only_remote_one_shot_authorization(self) -> None:
        body = self._body()
        blocked = self.client.post(self._url(), json=body)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        authorization = blocked.json()["detail"]["authorization"]
        self.assertEqual(authorization["consent_required"], ["remote_execution"])
        self.assertEqual(authorization["cost_estimate"]["state"], "not_applicable")
        self.assertEqual(self.runtime.calls, [])

        authorized = self.client.post(
            self._url("authorize-execution"),
            json={**body, "acknowledgements": ["remote_execution"]},
        )
        self.assertEqual(authorized.status_code, 200, authorized.text)
        token = authorized.json()["authorization_token"]

        executed = self.client.post(
            self._url(),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(executed.status_code, 200, executed.text)
        self.assertEqual(len(self.runtime.calls), 1)
        output = executed.json()["result"]["output"]
        artifact = output["artifact"]
        self.assertTrue(artifact.startswith("artifacts/run_"))
        self.assertTrue(
            self.store.resolve_project_file(
                self.project.project_id,
                artifact,
                must_exist=True,
                allowed_roots=("artifacts",),
            ).is_file()
        )
        record = self._records()[0]
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(record["executor"]["kind"], "native_videoclaw")
        self.assertEqual(record["executor"]["identity"]["operation"], "edge_tts")
        self.assertEqual(record["authorization"]["consent_scopes"], ["remote_execution"])
        self.assertEqual(record["cost"]["class"], "free")
        self.assertNotIn(token, json.dumps(record))

        replay = self.client.post(
            self._url(),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(replay.status_code, 409, replay.text)
        self.assertEqual(replay.json()["detail"]["code"], "authorization_invalid")
        self.assertEqual(len(self.runtime.calls), 1)

    def test_local_free_first_never_widens_to_remote_free_native_offer(self) -> None:
        response = self.client.post(
            self._url(),
            json={"selection_policy": "local_free_first", "input": {"text": "Hello"}},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "offer_not_executable")
        self.assertEqual(self.runtime.calls, [])

    def test_mutated_input_cannot_reuse_authorization(self) -> None:
        body = self._body(text="Original")
        authorized = self.client.post(
            self._url("authorize-execution"),
            json={**body, "acknowledgements": ["remote_execution"]},
        )
        token = authorized.json()["authorization_token"]
        mutated = self._body(text="Changed")
        response = self.client.post(
            self._url(),
            json={**mutated, "authorization_token": token},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "authorization_invalid")
        self.assertEqual(self.runtime.calls, [])
        self.assertEqual(self._records(), [])

    def test_missing_dependency_is_truthful_and_does_not_create_run_record(self) -> None:
        self.runtime._available = False
        body = self._body()
        authorized = self.client.post(
            self._url("authorize-execution"),
            json={**body, "acknowledgements": ["remote_execution"]},
        )
        token = authorized.json()["authorization_token"]
        response = self.client.post(
            self._url(),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "native_videoclaw_dependency_unavailable",
        )
        self.assertEqual(self.runtime.calls, [])
        self.assertEqual(self._records(), [])

    def test_remote_failure_writes_controlled_failed_provenance(self) -> None:
        self.runtime.fail = True
        body = self._body()
        authorized = self.client.post(
            self._url("authorize-execution"),
            json={**body, "acknowledgements": ["remote_execution"]},
        )
        token = authorized.json()["authorization_token"]
        response = self.client.post(
            self._url(),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(response.json()["detail"]["code"], "native_videoclaw_remote_failed")
        record = self._records()[0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error"]["code"], "native_videoclaw_remote_failed")
        self.assertNotIn("raw-provider-body-must-not-persist", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
