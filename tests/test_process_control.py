from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from threading import Timer

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import (
    CapabilityExecutionCancelled,
    CapabilityToolUnavailable,
)
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.capabilities.process_control import CancellationToken, CancellableProcessRunner
from uv_studio.projects.store import ProjectStore


class CancellableProcessRunnerTests(unittest.TestCase):
    def test_pre_cancelled_token_never_starts_process(self) -> None:
        token = CancellationToken()
        token.cancel()
        runner = CancellableProcessRunner(token)
        with self.assertRaises(CapabilityExecutionCancelled):
            runner(
                [sys.executable, "-c", "raise SystemExit(99)"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
            )

    def test_live_child_is_terminated_before_it_can_publish_late_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "late.txt"
            token = CancellationToken()
            runner = CancellableProcessRunner(
                token,
                poll_interval_sec=0.02,
                termination_grace_sec=0.2,
            )
            timer = Timer(0.15, token.cancel)
            timer.start()
            started = time.monotonic()
            try:
                with self.assertRaises(CapabilityExecutionCancelled):
                    runner(
                        [
                            sys.executable,
                            "-c",
                            (
                                "import pathlib,sys,time; "
                                "time.sleep(5); "
                                "pathlib.Path(sys.argv[1]).write_text('late', encoding='utf-8')"
                            ),
                            str(marker),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=False,
                    )
            finally:
                timer.cancel()
            self.assertLess(time.monotonic() - started, 3.0)
            time.sleep(0.1)
            self.assertFalse(marker.exists())

    def test_timeout_remains_timeout_not_cancellation(self) -> None:
        token = CancellationToken()
        runner = CancellableProcessRunner(
            token,
            poll_interval_sec=0.01,
            termination_grace_sec=0.1,
        )
        with self.assertRaises(subprocess.TimeoutExpired):
            runner(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                check=False,
                capture_output=True,
                text=True,
                timeout=0.1,
                shell=False,
            )
        self.assertFalse(token.is_cancelled)


class LocalFFmpegCancellationBindingTests(unittest.TestCase):
    @staticmethod
    def _offer() -> CapabilityOffer:
        return CapabilityOffer(
            "local_ffmpeg.media_probe",
            "media.probe",
            "local_ffmpeg",
            "Probe",
            OfferAvailability.AVAILABLE,
            "test",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    def test_cancellable_execution_restores_injected_runner_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="cancel runner restore")
            source = store.project_directory(project.project_id) / "sources" / "clip.mp4"
            source.write_bytes(b"not-media")
            calls = []

            def injected_runner(command, **kwargs):
                calls.append((command, kwargs))
                raise AssertionError("injected runner must not be used by cancellable execution")

            adapter = LocalFFmpegAdapter(
                store,
                runner=injected_runner,
                tool_paths={"ffprobe": "uv-definitely-missing-ffprobe"},
            )
            with self.assertRaises(CapabilityToolUnavailable):
                adapter.execute(
                    project_id=project.project_id,
                    offer=self._offer(),
                    payload={"path": "sources/clip.mp4"},
                    cancellation=CancellationToken(),
                )
            self.assertIs(adapter._delegate.runner, injected_runner)
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
