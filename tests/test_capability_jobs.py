from __future__ import annotations

import time
import unittest
from threading import Event

from uv_studio.capabilities.execution import CapabilityExecutionCancelled
from uv_studio.capabilities.jobs import (
    CapabilityExecutionJobStore,
    CapabilityJobCapacityExceeded,
    CapabilityJobNotFound,
)


class CapabilityExecutionJobStoreTests(unittest.TestCase):
    def test_successful_job_publishes_only_terminal_result(self) -> None:
        store = CapabilityExecutionJobStore(max_jobs=4)
        created = store.create(
            project_id="project_a",
            capability_id="media.probe",
            offer_id="local_ffmpeg.media_probe",
            adapter_id="local_ffmpeg",
            executor=lambda cancellation: {"ok": True},
        )
        self.assertEqual(created["status"], "queued")
        self.assertIsNone(created["result"])
        terminal = store.wait_for_terminal(
            project_id="project_a",
            job_id=created["job_id"],
        )
        self.assertEqual(terminal["status"], "succeeded")
        self.assertEqual(terminal["result"], {"ok": True})
        self.assertIsNone(terminal["error"])

    def test_running_job_cancels_cooperatively_and_becomes_terminal(self) -> None:
        store = CapabilityExecutionJobStore(max_jobs=4)
        started = Event()

        def execute(cancellation):
            started.set()
            while not cancellation.is_cancelled:
                time.sleep(0.01)
            cancellation.raise_if_cancelled()
            raise AssertionError("unreachable")

        created = store.create(
            project_id="project_a",
            capability_id="video.render_edits",
            offer_id="local_ffmpeg.video_render_edits",
            adapter_id="local_ffmpeg",
            executor=execute,
        )
        self.assertTrue(started.wait(1.0))
        cancelling = store.cancel(project_id="project_a", job_id=created["job_id"])
        self.assertTrue(cancelling["cancel_requested"])
        self.assertIn(cancelling["status"], {"cancelling", "cancelled"})
        terminal = store.wait_for_terminal(
            project_id="project_a",
            job_id=created["job_id"],
        )
        self.assertEqual(terminal["status"], "cancelled")
        self.assertIsNone(terminal["result"])
        self.assertIsNone(terminal["error"])

    def test_cancel_all_requests_shutdown_and_waits_for_workers(self) -> None:
        store = CapabilityExecutionJobStore(max_jobs=4)
        started = Event()

        def execute(cancellation):
            started.set()
            while not cancellation.is_cancelled:
                time.sleep(0.01)
            cancellation.raise_if_cancelled()
            raise AssertionError("unreachable")

        created = store.create(
            project_id="project_a",
            capability_id="video.render_edits",
            offer_id="local_ffmpeg.video_render_edits",
            adapter_id="local_ffmpeg",
            executor=execute,
        )
        self.assertTrue(started.wait(1.0))
        self.assertTrue(store.cancel_all(wait_timeout_sec=2.0))
        terminal = store.get(project_id="project_a", job_id=created["job_id"])
        self.assertEqual(terminal["status"], "cancelled")
        self.assertTrue(terminal["cancel_requested"])

    def test_cross_project_job_lookup_fails_closed(self) -> None:
        store = CapabilityExecutionJobStore(max_jobs=4)
        created = store.create(
            project_id="project_a",
            capability_id="media.probe",
            offer_id="local_ffmpeg.media_probe",
            adapter_id="local_ffmpeg",
            executor=lambda cancellation: {"ok": True},
        )
        with self.assertRaises(CapabilityJobNotFound):
            store.get(project_id="project_b", job_id=created["job_id"])
        with self.assertRaises(CapabilityJobNotFound):
            store.cancel(project_id="project_b", job_id=created["job_id"])

    def test_unexpected_exception_is_sanitized(self) -> None:
        store = CapabilityExecutionJobStore(max_jobs=4)

        def explode(cancellation):
            raise RuntimeError("private-path=/secret/developer/file")

        created = store.create(
            project_id="project_a",
            capability_id="media.probe",
            offer_id="local_ffmpeg.media_probe",
            adapter_id="local_ffmpeg",
            executor=explode,
        )
        terminal = store.wait_for_terminal(
            project_id="project_a",
            job_id=created["job_id"],
        )
        self.assertEqual(terminal["status"], "failed")
        self.assertEqual(terminal["error"]["code"], "capability_job_internal_error")
        self.assertNotIn("private-path", terminal["error"]["message"])
        self.assertNotIn("/secret", terminal["error"]["message"])

    def test_capacity_prunes_terminal_jobs_but_rejects_when_all_slots_are_active(self) -> None:
        store = CapabilityExecutionJobStore(max_jobs=1)
        blocker = Event()
        started = Event()

        def execute(cancellation):
            started.set()
            blocker.wait(2.0)
            if cancellation.is_cancelled:
                raise CapabilityExecutionCancelled("cancelled")
            return {"ok": True}

        created = store.create(
            project_id="project_a",
            capability_id="media.probe",
            offer_id="local_ffmpeg.media_probe",
            adapter_id="local_ffmpeg",
            executor=execute,
        )
        self.assertTrue(started.wait(1.0))
        with self.assertRaises(CapabilityJobCapacityExceeded):
            store.create(
                project_id="project_a",
                capability_id="media.probe",
                offer_id="local_ffmpeg.media_probe",
                adapter_id="local_ffmpeg",
                executor=lambda cancellation: {"ok": True},
            )
        store.cancel(project_id="project_a", job_id=created["job_id"])
        blocker.set()
        store.wait_for_terminal(project_id="project_a", job_id=created["job_id"])
        replacement = store.create(
            project_id="project_a",
            capability_id="media.probe",
            offer_id="local_ffmpeg.media_probe",
            adapter_id="local_ffmpeg",
            executor=lambda cancellation: {"replacement": True},
        )
        self.assertNotEqual(replacement["job_id"], created["job_id"])


if __name__ == "__main__":
    unittest.main()
