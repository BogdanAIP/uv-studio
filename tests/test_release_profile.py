from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from uv_studio.release_profile import ReleaseProfileError, load_release_profile
from tools.export_release_profile import DEFAULT_PROFILE, ROOT, profile_environment


class ReleaseProfileTests(unittest.TestCase):
    def _write_profile(self, profile: dict[str, object], root: str) -> Path:
        path = Path(root) / "profile.json"
        path.write_text(json.dumps(profile), encoding="utf-8")
        return path

    def test_direct_exporter_entrypoint_can_import_uv_studio_outside_repo_cwd(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "export_release_profile.py"), "--help"],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Export the validated Windows release profile", result.stdout)

    def test_checked_in_profile_has_exact_release_inputs(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        self.assertEqual(profile["schema_version"], 4)
        self.assertEqual(profile["target"], {"os": "windows", "arch": "x86_64"})
        self.assertEqual(profile["python"]["version"], "3.13.14")
        self.assertEqual(profile["node"]["version"], "24.19.0")
        self.assertEqual(
            profile["node"]["download"]["url"],
            "https://nodejs.org/download/release/v24.19.0/node-v24.19.0-win-x64.zip",
        )
        self.assertEqual(
            profile["node"]["download"]["sha256"],
            "57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73",
        )
        self.assertEqual(profile["media"]["distribution"], "shotcut-portable")
        self.assertEqual(profile["media"]["version"], "26.4.30")
        self.assertEqual(
            profile["media"]["download"]["url"],
            "https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-win64-26.4.30.zip",
        )
        self.assertEqual(
            profile["media"]["download"]["sha256"],
            "986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a",
        )
        self.assertEqual(profile["build_tools"]["pyinstaller"], "6.21.0")
        nsis = profile["build_tools"]["nsis"]
        self.assertEqual(nsis["version"], "3.12")
        self.assertEqual(
            nsis["acquisition"],
            {
                "provider": "chocolatey",
                "package": "nsis.install",
                "package_version": "3.12.0",
                "source": "https://community.chocolatey.org/api/v2/",
            },
        )

    def test_export_uses_package_version_as_product_version(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        values = profile_environment(profile)
        from uv_studio import __version__

        self.assertEqual(values["UV_PRODUCT_VERSION"], __version__)
        self.assertEqual(values["UV_PYTHON_VERSION"], "3.13.14")
        self.assertEqual(values["UV_NODE_VERSION"], "24.19.0")
        self.assertEqual(values["UV_MEDIA_DISTRIBUTION"], "shotcut-portable")
        self.assertEqual(values["UV_MEDIA_PACKAGE_VERSION"], "26.4.30")
        self.assertEqual(values["UV_PYINSTALLER_VERSION"], "6.21.0")
        self.assertEqual(values["UV_NSIS_VERSION"], "3.12")
        self.assertEqual(values["UV_NSIS_PROVIDER"], "chocolatey")
        self.assertEqual(values["UV_NSIS_PACKAGE"], "nsis.install")
        self.assertEqual(values["UV_NSIS_PACKAGE_VERSION"], "3.12.0")
        self.assertEqual(values["UV_NSIS_SOURCE"], "https://community.chocolatey.org/api/v2/")
        self.assertNotIn("UV_NSIS_URL", values)
        self.assertNotIn("UV_NSIS_SHA256", values)

    def test_profile_rejects_download_hash_drift(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        profile["node"]["download"]["sha256"] = "A" * 64
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(self._write_profile(profile, tmp))

    def test_profile_rejects_unsafe_nsis_acquisition(self) -> None:
        mutations = (
            ("provider", "winget"),
            ("package", "--source=https://example.invalid"),
            ("package_version", "3.12.0 --force"),
            ("source", "http://community.chocolatey.org/api/v2/"),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                profile = load_release_profile(DEFAULT_PROFILE)
                profile["build_tools"]["nsis"]["acquisition"][key] = value
                with tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(ReleaseProfileError):
                        load_release_profile(self._write_profile(profile, tmp))

    def test_profile_rejects_unknown_fields_and_unsafe_relative_paths(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        profile["unexpected"] = True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(self._write_profile(profile, tmp))

        profile = load_release_profile(DEFAULT_PROFILE)
        profile["python"]["constraints"] = "../escape.txt"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(self._write_profile(profile, tmp))

        profile = load_release_profile(DEFAULT_PROFILE)
        profile["build_tools"]["nsis"]["unexpected"] = True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(self._write_profile(profile, tmp))


if __name__ == "__main__":
    unittest.main()
