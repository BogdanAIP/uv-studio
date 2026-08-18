from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.media_runtime_closure import (
    carrier_path_is_required,
    exact_closure_root_files,
    prune_media_runtime_carrier,
)


class MediaRuntimeClosureTests(unittest.TestCase):
    def test_required_paths_are_narrow_and_case_insensitive(self) -> None:
        self.assertTrue(carrier_path_is_required("ffmpeg.exe"))
        self.assertTrue(carrier_path_is_required("QT6CORE.DLL"))
        self.assertTrue(carrier_path_is_required("lib/mlt/libmltavformat.dll"))
        self.assertTrue(carrier_path_is_required("lib/qt6/platforms/qwindows.dll"))
        self.assertTrue(carrier_path_is_required("share/mlt/core/loader.ini"))
        self.assertFalse(carrier_path_is_required("ggml-vulkan.dll"))
        self.assertFalse(carrier_path_is_required("lib/mlt/libmltopencv.dll"))
        self.assertFalse(carrier_path_is_required("lib/qt6/imageformats/qjpeg.dll"))
        self.assertFalse(carrier_path_is_required("share/translations/qt_en.qm"))

    def test_prune_removes_unreachable_carrier_surface_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keep = (
                root / "ffmpeg.exe",
                root / "Qt6Core.dll",
                root / "lib" / "mlt" / "libmltcore.dll",
                root / "lib" / "qt6" / "platforms" / "qwindows.dll",
                root / "share" / "mlt" / "core" / "loader.ini",
            )
            remove = (
                root / "ggml-vulkan.dll",
                root / "lib" / "mlt" / "libmltopencv.dll",
                root / "lib" / "qt6" / "imageformats" / "qjpeg.dll",
                root / "share" / "translations" / "qt_en.qm",
            )
            for path in (*keep, *remove):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")

            removed = prune_media_runtime_carrier(root)

            self.assertEqual(removed, len(remove))
            for path in keep:
                self.assertTrue(path.is_file())
            for path in remove:
                self.assertFalse(path.exists())
            self.assertFalse((root / "share" / "translations").exists())

    def test_exact_root_closure_contains_entrypoints_and_framework(self) -> None:
        names = exact_closure_root_files()
        for required in (
            "ffmpeg.exe",
            "ffprobe.exe",
            "melt.exe",
            "libmlt-7.dll",
            "libmlt++-7.dll",
            "qt6core.dll",
            "sdl2.dll",
        ):
            self.assertIn(required.casefold(), names)
        self.assertNotIn("shotcut.exe", names)
        self.assertNotIn("libopencv_core4140.dll", names)


if __name__ == "__main__":
    unittest.main()
