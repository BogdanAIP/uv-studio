from __future__ import annotations

import shutil
import time
import unittest
from threading import Timer

from uv_studio.capabilities.execution import CapabilityExecutionCancelled
from uv_studio.capabilities.process_control import CancellationToken, CancellableProcessRunner


class FFmpegCancellationRealMediaTests(unittest.TestCase):
    def test_real_ffmpeg_process_is_terminated_by_cancellation_token(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.skipTest("FFmpeg is not provisioned for real-media evidence")

        token = CancellationToken()
        runner = CancellableProcessRunner(
            token,
            poll_interval_sec=0.02,
            termination_grace_sec=1.0,
        )
        timer = Timer(0.35, token.cancel)
        timer.start()
        started = time.monotonic()
        try:
            with self.assertRaises(CapabilityExecutionCancelled):
                runner(
                    [
                        ffmpeg,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-re",
                        "-f",
                        "lavfi",
                        "-i",
                        "testsrc2=size=320x180:rate=30",
                        "-t",
                        "30",
                        "-f",
                        "null",
                        "-",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=35,
                    shell=False,
                )
        finally:
            timer.cancel()

        self.assertLess(
            time.monotonic() - started,
            5.0,
            "real FFmpeg cancellation must not wait for the 30-second input to finish",
        )
        self.assertTrue(token.is_cancelled)


if __name__ == "__main__":
    unittest.main()
