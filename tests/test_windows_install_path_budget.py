from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.check_windows_install_paths import analyze_install_path_budget
from uv_studio.release_manifest import (
    ReleaseComponent,
    build_release_manifest,
    write_release_manifest,
)


class WindowsInstallPathBudgetTests(unittest.TestCase):
    def _release(self, root: Path, *, extra_path: str = "runtime/media/bin/ffmpeg.exe") -> None:
        files = {
            "backend/uv-studio-backend.exe": b"backend",
            "frontend/server.js": b"frontend",
            "runtime/node/node.exe": b"node",
            "desktop/uv-studio-desktop.exe": b"desktop",
            extra_path: b"ffmpeg",
            "runtime/media/bin/ffprobe.exe": b"ffprobe",
            "runtime/media/bin/melt.exe": b"melt",
        }
        for relative, content in files.items():
            target = root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        manifest = build_release_manifest(
            root,
            product_version="0.1.0-dev",
            build_id="path-budget-test",
            target_arch="x86_64",
            components=(
                ReleaseComponent("backend", "0.1.0-dev", "backend/uv-studio-backend.exe"),
                ReleaseComponent("frontend", "0.1.0-dev", "frontend/server.js"),
                ReleaseComponent("node", "24.19.0", "runtime/node/node.exe"),
                ReleaseComponent("desktop", "0.1.0-dev", "desktop/uv-studio-desktop.exe"),
                ReleaseComponent("ffmpeg", "media", extra_path),
                ReleaseComponent("ffprobe", "media", "runtime/media/bin/ffprobe.exe"),
                ReleaseComponent("mlt", "media", "runtime/media/bin/melt.exe"),
            ),
        )
        write_release_manifest(manifest, root)

    def test_short_release_fits_classic_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._release(root)
            report = analyze_install_path_budget(
                root,
                r"C:\Users\runneradmin\AppData\Local\Programs\UV Studio\versions\release-a",
            )
            self.assertTrue(report["ok"])
            self.assertEqual(report["violation_count"], 0)
            self.assertEqual(report["checked_paths"], 8)

    def test_deep_release_reports_exact_offending_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deep = "runtime/media/" + "/".join(["very-long-directory-name"] * 9) + "/ffmpeg.exe"
            self._release(root, extra_path=deep)
            report = analyze_install_path_budget(
                root,
                r"C:\Users\runneradmin\AppData\Local\Programs\UV Studio\versions\release-a",
            )
            self.assertFalse(report["ok"])
            self.assertGreater(report["violation_count"], 0)
            self.assertEqual(report["violations"][0]["path"], deep)

    def test_install_root_must_be_absolute_windows_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._release(root)
            with self.assertRaisesRegex(ValueError, "absolute Windows path"):
                analyze_install_path_budget(root, r"versions\release-a")


if __name__ == "__main__":
    unittest.main()
