from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.release_profile import ReleaseProfileError, load_release_profile
from tools.export_release_profile import DEFAULT_PROFILE, profile_environment


class ReleaseProfileTests(unittest.TestCase):
    def test_checked_in_profile_has_exact_release_inputs(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        self.assertEqual(profile["schema_version"], 3)
        self.assertEqual(profile["target"], {"os": "windows", "arch": "x86_64"})
        self.assertEqual(profile["python"]["version"], "3.13.14")
        self.assertEqual(profile["node"]["version"], "24.19.0")
        self.assertEqual(
            profile["node"]["download"]["sha256"],
            "3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237",
        )
        self.assertEqual(profile["media"]["distribution"], "kdenlive-standalone")
        self.assertEqual(profile["media"]["version"], "26.04.3")
        self.assertEqual(
            profile["media"]["download"]["sha256"],
            "f2dc616c9c29cae261a4e4fc56293f5e88362b8024dc0b8f662c480c97e18df9",
        )
        self.assertEqual(profile["build_tools"]["pyinstaller"], "6.21.0")
        self.assertEqual(profile["build_tools"]["nsis"]["version"], "3.12")
        self.assertEqual(
            profile["build_tools"]["nsis"]["download"]["sha256"],
            "56581f90db321581c5381193d796fffcf2d24b2f8fed2160a6c6a3baa67f2c4f",
        )

    def test_export_uses_package_version_as_product_version(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        values = profile_environment(profile)
        from uv_studio import __version__

        self.assertEqual(values["UV_PRODUCT_VERSION"], __version__)
        self.assertEqual(values["UV_PYTHON_VERSION"], "3.13.14")
        self.assertEqual(values["UV_NODE_VERSION"], "24.19.0")
        self.assertEqual(values["UV_MEDIA_PACKAGE_VERSION"], "26.04.3")
        self.assertEqual(values["UV_PYINSTALLER_VERSION"], "6.21.0")
        self.assertEqual(values["UV_NSIS_VERSION"], "3.12")
        self.assertTrue(values["UV_NSIS_URL"].startswith("https://sourceforge.net/"))
        self.assertEqual(
            values["UV_NSIS_SHA256"],
            "56581f90db321581c5381193d796fffcf2d24b2f8fed2160a6c6a3baa67f2c4f",
        )

    def test_profile_rejects_download_hash_drift(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        profile["node"]["download"]["sha256"] = "A" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(path)

        profile = load_release_profile(DEFAULT_PROFILE)
        profile["build_tools"]["nsis"]["download"]["sha256"] = "0" * 63
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(path)

    def test_profile_rejects_unknown_fields_and_unsafe_relative_paths(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        profile["unexpected"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(path)

        profile = load_release_profile(DEFAULT_PROFILE)
        profile["python"]["constraints"] = "../escape.txt"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(path)

        profile = load_release_profile(DEFAULT_PROFILE)
        profile["build_tools"]["nsis"]["unexpected"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(path)


if __name__ == "__main__":
    unittest.main()
