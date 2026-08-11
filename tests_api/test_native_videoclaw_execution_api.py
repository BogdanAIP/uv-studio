from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_native_videoclaw_adapter,
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


class StubNativeVideoClawExecutor:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, *, project_id, offer, preparation, payload):
        self.calls.append((project_id, offer, preparation, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={
                "run_id": "run_stub",
                "path": "artifacts/art_stub.mp3",
                "voice": payload.get("voice", "zh-CN-YunjianNeural"),
                "speed": float(payload.get("speed", 1.0)),
            },
        )


class NativeVideoClawExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Edge TTS API")
        self.registry = self._registry()
        self.executor = StubNativeVideoClawExecutor()
        self.authorizations = OneShotAuthorizationStore()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_native_videoclaw_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = lambda: self.authorizations
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        speech = CapabilityDefinition(
            "speech.synthesize",
            "Speech synthesis",
            "Synthesize speech from text",
            OperationKind.SPEECH,
            (MediaKind.TEXT,),
            (MediaKind.AUDIO,),
            asynchronous=True,
        )
        adapter = AdapterDefinition(
            "native_videoclaw",
            "Native VideoClaw",
            "Compatibility adapter",
            AdapterKind.NATIVE,
        )
        registry = CapabilityRegistry((speech,), (adapter,))
        registry.register_offer(
            CapabilityOffer(
                "native_videoclaw.edge_tts",
                "speech.synthesize",
                "native_videoclaw",
                "Edge TTS",
                OfferAvailability.AVAILABLE,
                "edge-tts installed",
                LocalityClass.REMOTE,
                CostClass.FREE,
                True,
                ("speech.keyless",),
            )
        )
        return registry

    def _url(self, action: str = "execute") -> str:
        return (
            f"/api/uv/projects/{self.project.project_id}"
            f"/capabilities/speech.synthesize/{action}"
        )

    @staticmethod
    def _body() -> dict:
        return {
            "selection_policy": "pinned_offer",
            "offer_id": "native_videoclaw.edge_tts",
            "input": {
                "text": "Hello from authorized Edge TTS",
                "voice": "en-US-AriaNeural",
                "speed": 1.1,
            },
        }

    def test_remote_edge_tts_cannot_execute_before_one_shot_authorization(self) -> None:
        body = self._body()
        blocked = self.client.post(self._url(), json=body)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        detail = blocked.json()["detail"]
        self.assertEqual(detail["code"], "consent_required")
        self.assertEqual(
            detail["authorization"]["consent_required"],
            ["remote_execution"],
        )
        self.assertEqual(
            detail["authorization"]["cost_estimate"]["state"],
            "not_applicable",
        )
        self.assertEqual(self.executor.calls, [])

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
        payload = executed.json()
        self.assertEqual(
            payload["selection"]["offer"]["offer_id"],
            "native_videoclaw.edge_tts",
        )
        self.assertEqual(payload["result"]["output"]["path"], "artifacts/art_stub.mp3")
        self.assertEqual(len(self.executor.calls), 1)
        preparation = self.executor.calls[0][2]
        self.assertEqual(
            [scope.value for scope in preparation.consent_required],
            ["remote_execution"],
        )

        replay = self.client.post(
            self._url(),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(replay.status_code, 409, replay.text)
        self.assertEqual(replay.json()["detail"]["code"], "authorization_invalid")
        self.assertEqual(len(self.executor.calls), 1)

    def test_authorization_token_cannot_be_reused_for_mutated_speech_input(self) -> None:
        body = self._body()
        authorized = self.client.post(
            self._url("authorize-execution"),
            json={**body, "acknowledgements": ["remote_execution"]},
        )
        self.assertEqual(authorized.status_code, 200, authorized.text)
        token = authorized.json()["authorization_token"]

        mutated = self.client.post(
            self._url(),
            json={
                **body,
                "input": {**body["input"], "text": "mutated after authorization"},
                "authorization_token": token,
            },
        )
        self.assertEqual(mutated.status_code, 409, mutated.text)
        self.assertEqual(mutated.json()["detail"]["code"], "authorization_invalid")
        self.assertEqual(self.executor.calls, [])

    def test_local_free_first_does_not_widen_to_remote_edge_tts(self) -> None:
        response = self.client.post(
            self._url(),
            json={
                "selection_policy": "local_free_first",
                "input": {"text": "no remote fallback"},
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "offer_not_executable")
        self.assertEqual(self.executor.calls, [])


if __name__ == "__main__":
    unittest.main()
