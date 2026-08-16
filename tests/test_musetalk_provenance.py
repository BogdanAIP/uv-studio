from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities.adapters.musetalk import MUSE_TALK_UPSTREAM_COMMIT
from uv_studio.capabilities.adapters.musetalk_verified import (
    MUSE_TALK_INFERENCE_BLOB_SHA1,
    _checkout_problem,
    _git_blob_sha1,
)


class MuseTalkProvenanceTests(unittest.TestCase):
    @staticmethod
    def _runner(*, head: str, dirty: str = ""):
        def run(command, **kwargs):
            if "rev-parse" in command:
                return subprocess.CompletedProcess(command, 0, head + "\n", "")
            if "status" in command:
                return subprocess.CompletedProcess(command, 0, dirty, "")
            raise AssertionError(command)
        return run

    def test_wrong_or_dirty_checkout_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "inference.py").write_bytes(b"placeholder")
            with mock.patch(
                "uv_studio.capabilities.adapters.musetalk_verified._git_blob_sha1",
                return_value=MUSE_TALK_INFERENCE_BLOB_SHA1,
            ):
                wrong = _checkout_problem(
                    root,
                    runner=self._runner(head="0" * 40),
                    git_path="git",
                )
                dirty = _checkout_problem(
                    root,
                    runner=self._runner(head=MUSE_TALK_UPSTREAM_COMMIT, dirty=" M scripts/inference.py\n"),
                    git_path="git",
                )
        self.assertIn("pinned", wrong or "")
        self.assertIn("clean", dirty or "")

    def test_exact_clean_checkout_also_requires_pinned_inference_blob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            inference = root / "scripts" / "inference.py"
            inference.write_bytes(b"different inference")
            mismatch = _checkout_problem(
                root,
                runner=self._runner(head=MUSE_TALK_UPSTREAM_COMMIT),
                git_path="git",
            )
        self.assertIn("pinned upstream blob", mismatch or "")

    def test_git_blob_hash_matches_git_object_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file.py"
            body = b"print('uv')\n"
            path.write_bytes(body)
            expected = hashlib.sha1(
                f"blob {len(body)}\0".encode("ascii") + body,
                usedforsecurity=False,
            ).hexdigest()
            self.assertEqual(_git_blob_sha1(path), expected)


if __name__ == "__main__":
    unittest.main()
