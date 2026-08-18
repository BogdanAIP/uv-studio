from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.audit_ffmpeg_release import (
    FFmpegReleaseAuditError,
    MAX_BUILD_INFO_BYTES,
    inspect_ffmpeg,
)


class FFmpegReleaseAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ffmpeg = Path(self.tmp.name) / "ffmpeg.exe"
        self.ffmpeg.write_bytes(b"fixture")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _completed(output: bytes, *, returncode: int = 0) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=["ffmpeg", "-hide_banner", "-buildconf"],
            returncode=returncode,
            stdout=output,
            stderr=b"",
        )

    def test_nonfree_build_is_rejected_fail_closed(self) -> None:
        output = b"configuration:\n  --enable-gpl\n  --enable-nonfree\n  --enable-shared\n"
        with patch(
            "tools.audit_ffmpeg_release.subprocess.run",
            return_value=self._completed(output),
        ):
            with self.assertRaisesRegex(FFmpegReleaseAuditError, "enable-nonfree"):
                inspect_ffmpeg(self.ffmpeg)

    def test_gpl_shared_build_without_nonfree_is_reported_and_accepted(self) -> None:
        output = (
            b"ffmpeg version fixture\nconfiguration:\n"
            b"  --enable-gpl\n  --enable-version3\n"
            b"  --enable-shared\n  --disable-static\n"
        )
        with patch(
            "tools.audit_ffmpeg_release.subprocess.run",
            return_value=self._completed(output),
        ) as run:
            result = inspect_ffmpeg(self.ffmpeg)
        self.assertTrue(result["ok"])
        self.assertFalse(result["nonfree_enabled"])
        self.assertTrue(result["gpl_enabled"])
        self.assertTrue(result["shared_enabled"])
        self.assertTrue(result["static_disabled"])
        self.assertIn("--enable-gpl", result["configuration"])
        run.assert_called_once()
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_probe_failure_and_oversized_output_are_rejected(self) -> None:
        with patch(
            "tools.audit_ffmpeg_release.subprocess.run",
            return_value=self._completed(b"failed", returncode=1),
        ):
            with self.assertRaisesRegex(FFmpegReleaseAuditError, "exit 1"):
                inspect_ffmpeg(self.ffmpeg)

        with patch(
            "tools.audit_ffmpeg_release.subprocess.run",
            return_value=self._completed(b"x" * (MAX_BUILD_INFO_BYTES + 1)),
        ):
            with self.assertRaisesRegex(FFmpegReleaseAuditError, "unexpectedly large"):
                inspect_ffmpeg(self.ffmpeg)

    def test_missing_or_symlink_executable_is_rejected(self) -> None:
        self.ffmpeg.unlink()
        with self.assertRaisesRegex(FFmpegReleaseAuditError, "missing"):
            inspect_ffmpeg(self.ffmpeg)

        target = Path(self.tmp.name) / "real.exe"
        target.write_bytes(b"fixture")
        try:
            self.ffmpeg.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaisesRegex(FFmpegReleaseAuditError, "symlink"):
            inspect_ffmpeg(self.ffmpeg)


if __name__ == "__main__":
    unittest.main()
