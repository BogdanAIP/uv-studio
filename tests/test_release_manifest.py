from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from uv_studio.release_manifest import (
    RELEASE_MANIFEST_FILENAME,
    ReleaseComponent,
    ReleaseManifest,
    ReleaseManifestError,
    build_release_manifest,
    load_release_manifest,
    verify_release_tree,
    write_release_manifest,
)


class ReleaseManifestTests(unittest.TestCase):
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

    def _manifest(self) -> ReleaseManifest:
        return build_release_manifest(
            self.root,
            product_version="0.1.0",
            build_id="test-build",
            target_arch="x86_64",
            components=self.components,
        )

    def test_build_write_load_and_deep_verify_exact_release(self) -> None:
        manifest = self._manifest()
        path = write_release_manifest(manifest, self.root)
        self.assertEqual(path.name, RELEASE_MANIFEST_FILENAME)
        loaded = load_release_manifest(self.root)
        self.assertEqual(loaded, manifest)
        verification = verify_release_tree(loaded, self.root, verify_hashes=True)
        self.assertTrue(verification["ok"], verification)
        self.assertEqual(verification["checked_files"], len(self.payloads))
        self.assertTrue(verification["verify_hashes"])

    def test_deep_verify_rejects_same_size_payload_substitution(self) -> None:
        manifest = self._manifest()
        write_release_manifest(manifest, self.root)
        target = self.root / "media/ffmpeg.exe"
        target.write_bytes(b"X" * len(self.payloads["media/ffmpeg.exe"]))
        shallow = verify_release_tree(manifest, self.root, verify_hashes=False)
        self.assertTrue(shallow["ok"], shallow)
        deep = verify_release_tree(manifest, self.root, verify_hashes=True)
        self.assertFalse(deep["ok"])
        self.assertTrue(any("sha256 mismatch for media/ffmpeg.exe" in item for item in deep["problems"]))

    def test_verify_rejects_unlisted_release_file(self) -> None:
        manifest = self._manifest()
        write_release_manifest(manifest, self.root)
        extra = self.root / "runtime" / "shadow.py"
        extra.write_text("print('shadow')\n", encoding="utf-8")
        verification = verify_release_tree(manifest, self.root, verify_hashes=False)
        self.assertFalse(verification["ok"])
        self.assertTrue(any("unlisted release files" in item for item in verification["problems"]))

    def test_manifest_rejects_path_traversal(self) -> None:
        data = self._manifest().to_dict()
        data["files"][0]["path"] = "../escape.exe"
        with self.assertRaises(ReleaseManifestError):
            ReleaseManifest.from_dict(data)

    def test_manifest_rejects_component_entrypoint_missing_from_inventory(self) -> None:
        data = self._manifest().to_dict()
        data["components"][0]["entrypoint"] = "backend/missing.exe"
        with self.assertRaises(ReleaseManifestError):
            ReleaseManifest.from_dict(data)

    def test_build_rejects_symlink_payload_when_supported(self) -> None:
        link = self.root / "media" / "shadow.exe"
        try:
            os.symlink(self.root / "media" / "ffmpeg.exe", link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        with self.assertRaises(ReleaseManifestError):
            self._manifest()

    def test_manifest_json_contains_no_host_absolute_paths(self) -> None:
        manifest = self._manifest()
        encoded = json.dumps(manifest.to_dict(), sort_keys=True)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("\\\\", encoded)


if __name__ == "__main__":
    unittest.main()
