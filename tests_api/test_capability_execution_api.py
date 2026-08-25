from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
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


class StubLocalExecutor:
    def __init__(self) -> None:
        self.calls = []

    def execute(self, *, project_id, offer, payload):
        self.calls.append((project_id, offer, dict(payload)))
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"ok": True, "path": payload.get("path")},
        )


class CapabilityExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(recipe_id="general_video", title="Execution API")
        self.registry = self._registry()
        self.executor = StubLocalExecutor()
        self.authorizations = OneShotAuthorizationStore()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = lambda: self.authorizations
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> CapabilityRegistry:
        probe = CapabilityDefinition(
            "media.probe",
            "Probe",
            "probe local media",
            OperationKind.DETERMINISTIC_MEDIA,
            (MediaKind.VIDEO,),
            (MediaKind.METADATA,),
        )
        video = CapabilityDefinition(
            "video.generate",
            "Video",
            "generate video",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.VIDEO,),
            asynchronous=True,
        )
        adapters = (
            AdapterDefinition("local_ffmpeg", "Local FFmpeg", "local", AdapterKind.LOCAL),
            AdapterDefinition("native_videoclaw", "Native", "native", AdapterKind.NATIVE),
        )
        registry = CapabilityRegistry((probe, video), adapters)
        registry.register_offer(
            CapabilityOffer(
                "local_ffmpeg.media_probe",
                "media.probe",
                "local_ffmpeg",
                "Probe",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "local_ffmpeg.paid_probe",
                "media.probe",
                "local_ffmpeg",
                "Paid probe",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.LOCAL,
                CostClass.PAID,
                False,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "native_videoclaw.video_generate",
                "video.generate",
                "native_videoclaw",
                "Video",
                OfferAvailability.AVAILABLE,
                "configured for test",
                LocalityClass.HYBRID,
                CostClass.POTENTIALLY_PAID,
                True,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "native_videoclaw.remote_free",
                "video.generate",
                "native_videoclaw",
                "Remote free",
                OfferAvailability.AVAILABLE,
                "configured for test",
                LocalityClass.REMOTE,
                CostClass.FREE,
                True,
            )
        )
        return registry

    def _url(
        self,
        capability_id: str,
        action: str = "execute",
        project_id: str | None = None,
    ) -> str:
        return (
            f"/api/uv/projects/{project_id or self.project.project_id}"
            f"/capabilities/{capability_id}/{action}"
        )

    def test_local_free_first_executes_without_authorization(self) -> None:
        response = self.client.post(
            self._url("media.probe"),
            json={"selection_policy": "local_free_first", "input": {"path": "sources/a.mp4"}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["selection"]["offer"]["offer_id"], "local_ffmpeg.media_probe")
        self.assertEqual(payload["result"]["output"]["ok"], True)
        self.assertEqual(len(self.executor.calls), 1)

    def test_prepare_reports_local_free_as_not_applicable_cost(self) -> None:
        response = self.client.post(
            self._url("media.probe", "prepare-execution"),
            json={"selection_policy": "local_free_first", "input": {}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        authorization = response.json()["authorization"]
        self.assertFalse(authorization["authorization_required"])
        self.assertEqual(authorization["consent_required"], [])
        self.assertEqual(authorization["cost_estimate"]["state"], "not_applicable")

    def test_local_free_first_never_falls_through_to_potentially_paid(self) -> None:
        response = self.client.post(
            self._url("video.generate"),
            json={"selection_policy": "local_free_first", "input": {}},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(len(self.executor.calls), 0)
        self.assertEqual(response.json()["detail"]["code"], "offer_not_executable")

    def test_manual_policy_returns_choices_without_execution(self) -> None:
        response = self.client.post(
            self._url("media.probe"),
            json={"selection_policy": "manual", "input": {}},
        )
        self.assertEqual(response.status_code, 409, response.text)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "manual_selection_required")
        self.assertGreaterEqual(len(detail["offers"]), 2)
        self.assertEqual(len(self.executor.calls), 0)

    def test_paid_unknown_cost_requires_one_shot_authorization(self) -> None:
        body = {
            "selection_policy": "pinned_offer",
            "offer_id": "local_ffmpeg.paid_probe",
            "input": {"path": "sources/a.mp4"},
        }
        blocked = self.client.post(self._url("media.probe"), json=body)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        detail = blocked.json()["detail"]
        self.assertEqual(detail["code"], "consent_required")
        self.assertEqual(
            detail["authorization"]["consent_required"],
            ["external_cost", "unknown_cost"],
        )
        self.assertEqual(detail["authorization"]["cost_estimate"]["state"], "unknown")
        self.assertEqual(len(self.executor.calls), 0)

        incomplete = self.client.post(
            self._url("media.probe", "authorize-execution"),
            json={**body, "acknowledgements": ["external_cost"]},
        )
        self.assertEqual(incomplete.status_code, 409, incomplete.text)
        self.assertEqual(incomplete.json()["detail"]["code"], "acknowledgement_required")

        authorized = self.client.post(
            self._url("media.probe", "authorize-execution"),
            json={
                **body,
                "acknowledgements": ["external_cost", "unknown_cost"],
            },
        )
        self.assertEqual(authorized.status_code, 200, authorized.text)
        token = authorized.json()["authorization_token"]
        self.assertIsInstance(token, str)
        self.assertNotIn("authorization_token", authorized.json()["authorization"])

        executed = self.client.post(
            self._url("media.probe"),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(executed.status_code, 200, executed.text)
        self.assertEqual(len(self.executor.calls), 1)

        replay = self.client.post(
            self._url("media.probe"),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(replay.status_code, 409, replay.text)
        self.assertEqual(replay.json()["detail"]["code"], "authorization_invalid")
        self.assertEqual(len(self.executor.calls), 1)

    def test_authorization_is_bound_to_exact_normalized_input(self) -> None:
        body = {
            "selection_policy": "pinned_offer",
            "offer_id": "local_ffmpeg.paid_probe",
            "input": {"path": "sources/a.mp4", "options": {"b": 2, "a": 1}},
        }
        authorized = self.client.post(
            self._url("media.probe", "authorize-execution"),
            json={
                **body,
                "acknowledgements": ["external_cost", "unknown_cost"],
            },
        )
        token = authorized.json()["authorization_token"]

        mutated = self.client.post(
            self._url("media.probe"),
            json={
                **body,
                "input": {"path": "sources/other.mp4", "options": {"a": 1, "b": 2}},
                "authorization_token": token,
            },
        )
        self.assertEqual(mutated.status_code, 409, mutated.text)
        self.assertEqual(mutated.json()["detail"]["code"], "authorization_invalid")
        self.assertEqual(len(self.executor.calls), 0)

    def test_remote_free_requires_remote_permission_but_no_cost_ack(self) -> None:
        body = {
            "selection_policy": "pinned_offer",
            "offer_id": "native_videoclaw.remote_free",
            "input": {"prompt": "x"},
        }
        prepared = self.client.post(self._url("video.generate", "prepare-execution"), json=body)
        self.assertEqual(prepared.status_code, 200, prepared.text)
        authorization = prepared.json()["authorization"]
        self.assertEqual(authorization["consent_required"], ["remote_execution"])
        self.assertEqual(authorization["cost_estimate"]["state"], "not_applicable")

        authorized = self.client.post(
            self._url("video.generate", "authorize-execution"),
            json={**body, "acknowledgements": ["remote_execution"]},
        )
        token = authorized.json()["authorization_token"]
        executed = self.client.post(
            self._url("video.generate"),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(executed.status_code, 409, executed.text)
        self.assertEqual(executed.json()["detail"]["code"], "adapter_not_executable_yet")

    def test_potentially_paid_remote_reports_all_required_scopes(self) -> None:
        response = self.client.post(
            self._url("video.generate", "prepare-execution"),
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "native_videoclaw.video_generate",
                "input": {},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["authorization"]["consent_required"],
            ["remote_execution", "external_cost", "unknown_cost"],
        )

    def test_missing_project_is_404_before_execution(self) -> None:
        response = self.client.post(
            self._url("media.probe", project_id="prj_missing"),
            json={"selection_policy": "local_free_first", "input": {}},
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(len(self.executor.calls), 0)

    def test_unknown_request_field_is_rejected(self) -> None:
        response = self.client.post(
            self._url("media.probe"),
            json={"selection_policy": "local_free_first", "raw_ffmpeg_flags": ["-y"]},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(len(self.executor.calls), 0)


if __name__ == "__main__":
    unittest.main()
