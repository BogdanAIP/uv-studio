from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import get_local_ffmpeg_adapter
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
        self.project = self.store.create_project(title="Execution API")
        self.registry = self._registry()
        self.executor = StubLocalExecutor()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
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
        return registry

    def _url(self, capability_id: str, project_id: str | None = None) -> str:
        return (
            f"/api/uv/projects/{project_id or self.project.project_id}"
            f"/capabilities/{capability_id}/execute"
        )

    def test_local_free_first_executes_only_safe_local_offer(self) -> None:
        response = self.client.post(
            self._url("media.probe"),
            json={"selection_policy": "local_free_first", "input": {"path": "sources/a.mp4"}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["selection"]["offer"]["offer_id"], "local_ffmpeg.media_probe")
        self.assertEqual(payload["result"]["output"]["ok"], True)
        self.assertEqual(len(self.executor.calls), 1)

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

    def test_pinned_paid_offer_is_still_rejected_in_local_only_slice(self) -> None:
        response = self.client.post(
            self._url("media.probe"),
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "local_ffmpeg.paid_probe",
                "input": {"path": "sources/a.mp4"},
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "adapter_not_executable_yet")
        self.assertEqual(len(self.executor.calls), 0)

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
