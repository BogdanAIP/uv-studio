from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.diagnostics import build_diagnostics
from uv_studio.release_manifest import (
    ReleaseComponent,
    build_release_manifest,
    write_release_manifest,
)


class DiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "release"
        self.root.mkdir()
        self.payloads = {
            "backend/uv-studio-server.exe": b"backend-runtime",
            "frontend/server.js": b"frontend-runtime",
            "runtime/node/node.exe": b"node-runtime",
            "media/ffmpeg.exe": b"ffmpeg-runtime",
            "media/ffprobe.exe": b"ffprobe-runtime",
            "media/melt.exe": b"mlt-runtime",
        }
        for relative, body in self.payloads.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        self.components = (
            ReleaseComponent("backend", "0.1.0", "backend/uv-studio-server.exe"),
            ReleaseComponent("frontend", "16.2.12", "frontend/server.js"),
            ReleaseComponent("node", "20.0.0", "runtime/node/node.exe"),
            ReleaseComponent("ffmpeg", "test", "media/ffmpeg.exe"),
            ReleaseComponent("ffprobe", "test", "media/ffprobe.exe"),
            ReleaseComponent("mlt", "test", "media/melt.exe"),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_manifest(self) -> None:
        manifest = build_release_manifest(
            self.root,
            product_version="0.1.0",
            build_id="diagnostics-test",
            target_arch="x86_64",
            components=self.components,
        )
        write_release_manifest(manifest, self.root)

    def test_development_diagnostics_do_not_expose_secret_or_absolute_tool_paths(self) -> None:
        with mock.patch.dict(os.environ, {"UV_STUDIO_RELEASE_ROOT": ""}, clear=False):
            snapshot = build_diagnostics(
                tool_lookup=lambda tool: f"/private/developer/bin/{tool}"
            )
        self.assertEqual(snapshot["mode"], "development")
        self.assertEqual(snapshot["overall_status"], "ok")
        encoded = json.dumps(snapshot, sort_keys=True).lower()
        self.assertNotIn("/private/developer", encoded)
        self.assertNotIn("api_key", encoded)
        self.assertNotIn("bearer ", encoded)
        self.assertNotIn("secret_status", encoded)

    def test_packaged_diagnostics_deep_verify_exact_manifest(self) -> None:
        self._write_manifest()
        with mock.patch.dict(
            os.environ,
            {"UV_STUDIO_RELEASE_ROOT": str(self.root)},
            clear=False,
        ):
            snapshot = build_diagnostics(verify_release=True, tool_lookup=lambda _: None)
        self.assertEqual(snapshot["mode"], "packaged")
        self.assertEqual(snapshot["overall_status"], "ok")
        self.assertTrue(snapshot["release"]["manifest_valid"])
        self.assertTrue(snapshot["release"]["integrity"]["ok"])
        self.assertTrue(snapshot["release"]["integrity"]["verify_hashes"])
        self.assertEqual(snapshot["release"]["build_id"], "diagnostics-test")
        self.assertEqual(snapshot["release"]["components"]["ffmpeg"]["entrypoint"], "media/ffmpeg.exe")
        self.assertTrue(snapshot["media_tools"]["ffmpeg"]["available"])
        self.assertEqual(snapshot["media_tools"]["ffmpeg"]["source"], "release_manifest")

    def test_packaged_diagnostics_fail_closed_on_corrupt_manifest(self) -> None:
        (self.root / "release-manifest.json").write_text("{not json", encoding="utf-8")
        with mock.patch.dict(
            os.environ,
            {"UV_STUDIO_RELEASE_ROOT": str(self.root)},
            clear=False,
        ):
            snapshot = build_diagnostics(verify_release=True, tool_lookup=lambda _: None)
        self.assertEqual(snapshot["overall_status"], "invalid_release")
        self.assertFalse(snapshot["release"]["manifest_valid"])
        self.assertFalse(snapshot["release"]["integrity"]["ok"])
        self.assertTrue(snapshot["release"]["problems"])

    def test_packaged_diagnostics_report_same_size_substitution_on_deep_check(self) -> None:
        self._write_manifest()
        target = self.root / "media" / "ffprobe.exe"
        target.write_bytes(b"X" * len(self.payloads["media/ffprobe.exe"]))
        with mock.patch.dict(
            os.environ,
            {"UV_STUDIO_RELEASE_ROOT": str(self.root)},
            clear=False,
        ):
            shallow = build_diagnostics(verify_release=False, tool_lookup=lambda _: None)
            deep = build_diagnostics(verify_release=True, tool_lookup=lambda _: None)
        self.assertEqual(shallow["overall_status"], "ok")
        self.assertEqual(deep["overall_status"], "invalid_release")
        self.assertTrue(any("sha256 mismatch" in item for item in deep["release"]["problems"]))


if __name__ == "__main__":
    unittest.main()
