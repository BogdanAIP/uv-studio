from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.installed_release import (
    InstalledReleaseVerificationError,
    verify_installed_release,
)
from uv_studio.release_manifest import (
    ReleaseComponent,
    build_release_manifest,
    write_release_manifest,
)


class InstalledReleaseVerificationTests(unittest.TestCase):
    def _release(self, root: Path) -> Path:
        files = {
            "backend/uv-studio-backend.exe": b"backend-exe",
            "frontend/server.js": b"frontend-server",
            "runtime/node/node.exe": b"node-exe",
            "runtime/media/bin/ffmpeg.exe": b"ffmpeg-exe",
            "runtime/media/bin/ffprobe.exe": b"ffprobe-exe",
            "runtime/media/bin/melt.exe": b"melt-exe",
        }
        for relative, content in files.items():
            target = root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        components = (
            ReleaseComponent("backend", "0.1.0-dev", "backend/uv-studio-backend.exe"),
            ReleaseComponent("frontend", "0.1.0-dev", "frontend/server.js"),
            ReleaseComponent("node", "24.19.0", "runtime/node/node.exe"),
            ReleaseComponent("ffmpeg", "kdenlive-26.04.3", "runtime/media/bin/ffmpeg.exe"),
            ReleaseComponent("ffprobe", "kdenlive-26.04.3", "runtime/media/bin/ffprobe.exe"),
            ReleaseComponent("mlt", "kdenlive-26.04.3", "runtime/media/bin/melt.exe"),
        )
        manifest = build_release_manifest(
            root,
            product_version="0.1.0-dev",
            build_id="installed-release-test",
            target_arch="x86_64",
            components=components,
        )
        write_release_manifest(manifest, root)
        return root / "backend" / "uv-studio-backend.exe"

    def test_deep_install_verification_accepts_exact_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = self._release(root)
            result = verify_installed_release(
                release_root=root,
                current_executable=executable,
            )
            self.assertTrue(result["ok"])
            self.assertTrue(result["verify_hashes"])
            self.assertEqual(result["checked_files"], 6)
            self.assertEqual(result["problems"], [])

    def test_deep_install_verification_rejects_same_size_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = self._release(root)
            target = root / "frontend" / "server.js"
            data = bytearray(target.read_bytes())
            data[0] ^= 1
            target.write_bytes(data)
            with self.assertRaisesRegex(
                InstalledReleaseVerificationError,
                "deep integrity verification",
            ):
                verify_installed_release(
                    release_root=root,
                    current_executable=executable,
                )

    def test_install_preflight_preserves_bounded_missing_file_detail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = self._release(root)
            missing = root / "runtime" / "node" / "node.exe"
            missing.unlink()
            with self.assertRaises(InstalledReleaseVerificationError) as captured:
                verify_installed_release(
                    release_root=root,
                    current_executable=executable,
                )
            message = str(captured.exception)
            self.assertIn("installed release verification could not be completed", message)
            self.assertIn("runtime/node/node.exe", message)
            self.assertIn("missing", message.lower())


if __name__ == "__main__":
    unittest.main()
