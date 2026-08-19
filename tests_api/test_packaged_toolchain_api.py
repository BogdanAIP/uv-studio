from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.release_manifest import (
    ReleaseComponent,
    build_release_manifest,
    write_release_manifest,
)
from uv_studio.server import app
from uv_studio.toolchain import clear_toolchain_cache


class PackagedCapabilityToolchainApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.release = self.root / "release"
        self.release.mkdir()
        paths = {
            "backend": "backend/uv-studio-backend.exe",
            "frontend": "frontend/server.js",
            "node": "runtime/node/node.exe",
            "desktop": "desktop/uv-studio-desktop.exe",
            "ffmpeg": "media/ffmpeg.exe",
            "ffprobe": "media/ffprobe.exe",
            "mlt": "media/melt.exe",
        }
        for component_id, relative in paths.items():
            path = self.release / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"{component_id}-payload".encode("ascii"))
        manifest = build_release_manifest(
            self.release,
            product_version="0.1.0",
            build_id="capability-toolchain-test",
            target_arch="x86_64",
            components=tuple(
                ReleaseComponent(component_id, "test", relative)
                for component_id, relative in paths.items()
            ),
        )
        write_release_manifest(manifest, self.release)
        self.env = {
            "UV_STUDIO_RELEASE_ROOT": str(self.release),
            "UV_STUDIO_USER_DATA_DIR": str(self.root / "user-data"),
            "UV_STUDIO_PROJECTS_DIR": "",
            "UV_STUDIO_CONFIG_DIR": "",
        }
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        get_capability_registry.cache_clear()
        clear_toolchain_cache()
        self.tmp.cleanup()

    def test_packaged_local_ffmpeg_offers_use_verified_release_readiness_not_path(self) -> None:
        get_capability_registry.cache_clear()
        clear_toolchain_cache()
        with mock.patch.dict(os.environ, self.env, clear=False), mock.patch(
            "shutil.which", return_value=None
        ):
            response = self.client.get("/api/uv/capabilities/video.compose_photos/offers")
        self.assertEqual(response.status_code, 200, response.text)
        offers = response.json()
        offer = next(item for item in offers if item["adapter_id"] == "local_ffmpeg")
        self.assertEqual(offer["availability"], "available")
        self.assertIn("Verified UV Studio release", offer["reason"])
        self.assertNotIn("PATH", offer["reason"])

    def test_corrupt_packaged_ffmpeg_marks_local_offers_unavailable_without_path_fallback(self) -> None:
        ffmpeg = self.release / "media" / "ffmpeg.exe"
        ffmpeg.write_bytes(b"X" * ffmpeg.stat().st_size)
        get_capability_registry.cache_clear()
        clear_toolchain_cache()
        with mock.patch.dict(os.environ, self.env, clear=False), mock.patch(
            "shutil.which", return_value="C:/attacker/ffmpeg.exe"
        ):
            response = self.client.get("/api/uv/capabilities/video.compose_photos/offers")
        self.assertEqual(response.status_code, 200, response.text)
        offer = next(item for item in response.json() if item["adapter_id"] == "local_ffmpeg")
        self.assertEqual(offer["availability"], "unavailable")
        self.assertIn("integrity verification failed", offer["reason"])


if __name__ == "__main__":
    unittest.main()
