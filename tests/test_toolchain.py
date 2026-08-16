from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.projects.store import ProjectStore
from uv_studio.release_manifest import (
    ReleaseComponent,
    build_release_manifest,
    write_release_manifest,
)
from uv_studio.toolchain import (
    ToolchainResolutionError,
    clear_toolchain_cache,
    local_ffmpeg_tool_overrides,
    packaged_tool_paths,
    resolve_tool,
)


class PackagedToolchainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.release = self.root / "release"
        self.release.mkdir()
        self.paths = {
            "backend": "backend/uv-studio-backend.exe",
            "frontend": "frontend/server.js",
            "node": "runtime/node/node.exe",
            "ffmpeg": "media/ffmpeg.exe",
            "ffprobe": "media/ffprobe.exe",
            "mlt": "media/melt.exe",
        }
        for component_id, relative in self.paths.items():
            path = self.release / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"{component_id}-payload".encode("ascii"))
        components = tuple(
            ReleaseComponent(component_id, "test", relative)
            for component_id, relative in self.paths.items()
        )
        manifest = build_release_manifest(
            self.release,
            product_version="0.1.0",
            build_id="toolchain-test",
            target_arch="x86_64",
            components=components,
        )
        write_release_manifest(manifest, self.release)
        self.user_data = self.root / "user-data"

    def tearDown(self) -> None:
        clear_toolchain_cache()
        self.tmp.cleanup()

    def _env(self) -> dict[str, str]:
        return {
            "UV_STUDIO_RELEASE_ROOT": str(self.release),
            "UV_STUDIO_USER_DATA_DIR": str(self.user_data),
            "UV_STUDIO_PROJECTS_DIR": "",
            "UV_STUDIO_CONFIG_DIR": "",
        }

    def test_packaged_tool_resolution_ignores_system_path_shadow(self) -> None:
        attacker = self.root / "attacker" / "ffmpeg.exe"
        attacker.parent.mkdir()
        attacker.write_bytes(b"attacker")
        with mock.patch.dict(os.environ, self._env(), clear=False):
            resolved = resolve_tool(
                "ffmpeg",
                lookup=lambda _: str(attacker),
            )
        self.assertEqual(resolved, str((self.release / self.paths["ffmpeg"]).resolve()))
        self.assertNotEqual(resolved, str(attacker.resolve()))

    def test_packaged_tool_resolution_deep_verifies_same_size_substitution(self) -> None:
        target = self.release / self.paths["ffprobe"]
        target.write_bytes(b"X" * target.stat().st_size)
        clear_toolchain_cache()
        with mock.patch.dict(os.environ, self._env(), clear=False):
            with self.assertRaises(ToolchainResolutionError):
                packaged_tool_paths()

    def test_packaged_explicit_override_must_equal_verified_component(self) -> None:
        attacker = self.root / "attacker-ffmpeg.exe"
        attacker.write_bytes(b"attacker")
        with mock.patch.dict(os.environ, self._env(), clear=False):
            with self.assertRaises(ToolchainResolutionError):
                resolve_tool("ffmpeg", explicit=attacker)

    def test_local_ffmpeg_facade_injects_verified_release_tools(self) -> None:
        project_store = ProjectStore(self.root / "store")
        with mock.patch.dict(os.environ, self._env(), clear=False):
            adapter = LocalFFmpegAdapter(project_store)
            expected = local_ffmpeg_tool_overrides()
        self.assertEqual(adapter.tool_paths, expected)
        self.assertEqual(
            adapter.tool_paths["ffmpeg"],
            str((self.release / self.paths["ffmpeg"]).resolve()),
        )

    def test_development_mode_keeps_explicit_or_lookup_behavior(self) -> None:
        tool = self.root / "developer-ffmpeg"
        tool.write_bytes(b"dev")
        with mock.patch.dict(os.environ, {"UV_STUDIO_RELEASE_ROOT": ""}, clear=False):
            self.assertEqual(resolve_tool("ffmpeg", explicit=tool), str(tool.resolve()))
            self.assertEqual(
                resolve_tool("ffprobe", lookup=lambda _: "developer-ffprobe"),
                "developer-ffprobe",
            )


if __name__ == "__main__":
    unittest.main()
