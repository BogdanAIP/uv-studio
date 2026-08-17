from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from threading import Event

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import (
    get_execution_authorization_store,
    get_local_ffmpeg_adapter,
)
from uv_studio.api.capability_jobs import get_capability_job_store
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
from uv_studio.capabilities.jobs import CapabilityExecutionJobStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class StubCancellableLocalExecutor:
    def __init__(self) -> None:
        self.started = Event()
        self.calls = []
        self.cancellable = True

    def supports_cancellation(self, capability_id: str) -> bool:
        return self.cancellable and capability_id == "media.probe"

    def execute(self, *, project_id, offer, payload, cancellation=None):
        self.calls.append((project_id, offer.offer_id, dict(payload)))
        if payload.get("block"):
            self.started.set()
            while cancellation is not None and not cancellation.is_cancelled:
                time.sleep(0.01)
            if cancellation is not None:
                cancellation.raise_if_cancelled()
        return CapabilityExecutionResult.from_offer(
            project_id=project_id,
            offer=offer,
            output={"ok": True},
        )


class CapabilityJobsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Capability jobs")
        self.registry = CapabilityRegistry(
            (
                CapabilityDefinition(
                    "media.probe",
                    "Probe",
                    "probe local media",
                    OperationKind.DETERMINISTIC_MEDIA,
                    (MediaKind.VIDEO,),
                    (MediaKind.METADATA,),
                ),
            ),
            (
                AdapterDefinition(
                    "local_ffmpeg",
                    "Local FFmpeg",
                    "local media process adapter",
                    AdapterKind.LOCAL,
                ),
            ),
        )
        self.registry.register_offer(
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
        self.executor = StubCancellableLocalExecutor()
        self.authorizations = OneShotAuthorizationStore()
        self.jobs = CapabilityExecutionJobStore(max_jobs=8)
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: self.executor
        app.dependency_overrides[get_execution_authorization_store] = lambda: self.authorizations
        app.dependency_overrides[get_capability_job_store] = lambda: self.jobs
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _start_url(self) -> str:
        return (
            f"/api/uv/projects/{self.project.project_id}"
            "/capabilities/media.probe/jobs"
        )

    def _job_url(self, job_id: str, *, project_id: str | None = None) -> str:
        return (
            f"/api/uv/projects/{project_id or self.project.project_id}"
            f"/capability-jobs/{job_id}"
        )

    def test_job_can_be_cancelled_and_polled_to_terminal_state(self) -> None:
        started = self.client.post(
            self._start_url(),
            json={"selection_policy": "local_free_first", "input": {"block": True}},
        )
        self.assertEqual(started.status_code, 202, started.text)
        job = started.json()
        self.assertEqual(job["schema_version"], 1)
        self.assertEqual(job["project_id"], self.project.project_id)
        self.assertEqual(job["offer_id"], "local_ffmpeg.media_probe")
        self.assertIsNone(job["result"])
        self.assertTrue(self.executor.started.wait(1.0))

        cancelled = self.client.post(self._job_url(job["job_id"]) + "/cancel")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertTrue(cancelled.json()["cancel_requested"])
        self.assertIn(cancelled.json()["status"], {"cancelling", "cancelled"})

        deadline = time.monotonic() + 2.0
        terminal = None
        while time.monotonic() < deadline:
            response = self.client.get(self._job_url(job["job_id"]))
            self.assertEqual(response.status_code, 200, response.text)
            terminal = response.json()
            if terminal["status"] == "cancelled":
                break
            time.sleep(0.02)
        self.assertIsNotNone(terminal)
        self.assertEqual(terminal["status"], "cancelled")
        self.assertIsNone(terminal["result"])
        self.assertIsNone(terminal["error"])

    def test_successful_job_returns_existing_execution_envelope(self) -> None:
        started = self.client.post(
            self._start_url(),
            json={"selection_policy": "local_free_first", "input": {}},
        )
        self.assertEqual(started.status_code, 202, started.text)
        terminal = self.jobs.wait_for_terminal(
            project_id=self.project.project_id,
            job_id=started.json()["job_id"],
        )
        self.assertEqual(terminal["status"], "succeeded")
        self.assertEqual(
            terminal["result"]["selection"]["offer"]["offer_id"],
            "local_ffmpeg.media_probe",
        )
        self.assertTrue(terminal["result"]["result"]["output"]["ok"])

    def test_job_id_is_project_scoped(self) -> None:
        started = self.client.post(
            self._start_url(),
            json={"selection_policy": "local_free_first", "input": {}},
        )
        self.assertEqual(started.status_code, 202, started.text)
        hidden = self.client.get(
            self._job_url(started.json()["job_id"], project_id="another_project")
        )
        self.assertEqual(hidden.status_code, 404, hidden.text)
        self.assertEqual(hidden.json()["detail"]["code"], "capability_job_not_found")

    def test_adapter_without_proven_cancellation_fails_closed_before_execution(self) -> None:
        self.executor.cancellable = False
        response = self.client.post(
            self._start_url(),
            json={"selection_policy": "local_free_first", "input": {}},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "capability_job_cancellation_not_supported",
        )
        self.assertEqual(self.executor.calls, [])


if __name__ == "__main__":
    unittest.main()
