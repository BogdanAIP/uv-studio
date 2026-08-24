from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from uv_studio.release_profile import ReleaseProfileError, load_release_profile
from tools.export_release_profile import DEFAULT_PROFILE, ROOT, profile_environment


_NSIS_SOURCE_URL = "https://downloads.sourceforge.net/project/nsis/NSIS%203/3.12/nsis-3.12-src.tar.bz2"
_NSIS_SOURCE_SHA256 = "f3ed7a8e4aa2cf4e8cf47d3b563a02559e0cb4934db2662b2f9661b824e2b186"


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
        self.assertEqual(profile["schema_version"], 7)
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
        self.assertEqual(
            profile["desktop"],
            {
                "rust_version": "1.97.1",
                "cargo_lock": "desktop-host/Cargo.lock",
                "webview2_com_version": "0.39.1",
            },
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
        self.assertEqual(
            profile["media"]["corresponding_source"]["url"],
            "https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz",
        )
        self.assertEqual(
            profile["media"]["corresponding_source"]["sha256"],
            "fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442",
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
        self.assertEqual(
            nsis["corresponding_source"],
            {"url": _NSIS_SOURCE_URL, "sha256": _NSIS_SOURCE_SHA256},
        )

    def test_export_uses_package_version_as_product_version(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        values = profile_environment(profile)
        from uv_studio import __version__

        self.assertEqual(values["UV_PRODUCT_VERSION"], __version__)
        self.assertEqual(values["UV_PYTHON_VERSION"], "3.13.14")
        self.assertEqual(values["UV_NODE_VERSION"], "24.19.0")
        self.assertEqual(values["UV_RUST_VERSION"], "1.97.1")
        self.assertEqual(values["UV_DESKTOP_CARGO_LOCK"], "desktop-host/Cargo.lock")
        self.assertEqual(values["UV_WEBVIEW2_COM_VERSION"], "0.39.1")
        self.assertEqual(values["UV_MEDIA_DISTRIBUTION"], "shotcut-portable")
        self.assertEqual(values["UV_MEDIA_PACKAGE_VERSION"], "26.4.30")
        self.assertEqual(values["UV_PYINSTALLER_VERSION"], "6.21.0")
        self.assertEqual(values["UV_NSIS_VERSION"], "3.12")
        self.assertEqual(values["UV_NSIS_PROVIDER"], "chocolatey")
        self.assertEqual(values["UV_NSIS_PACKAGE"], "nsis.install")
        self.assertEqual(values["UV_NSIS_PACKAGE_VERSION"], "3.12.0")
        self.assertEqual(values["UV_NSIS_SOURCE"], "https://community.chocolatey.org/api/v2/")
        self.assertEqual(values["UV_NSIS_SOURCE_URL"], _NSIS_SOURCE_URL)
        self.assertEqual(values["UV_NSIS_SOURCE_SHA256"], _NSIS_SOURCE_SHA256)
        self.assertNotIn("UV_MEDIA_SOURCE_URL", values)
        self.assertNotIn("UV_MEDIA_SOURCE_SHA256", values)
        self.assertNotIn("UV_NSIS_URL", values)
        self.assertNotIn("UV_NSIS_SHA256", values)

    def test_profile_rejects_download_hash_drift(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        profile["node"]["download"]["sha256"] = "A" * 64
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(self._write_profile(profile, tmp))

    def test_profile_rejects_unsafe_desktop_inputs(self) -> None:
        mutations = (
            ("rust_version", "1.97.1 --default"),
            ("cargo_lock", "../Cargo.lock"),
            ("webview2_com_version", "0.39.1\nnext"),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                profile = load_release_profile(DEFAULT_PROFILE)
                profile["desktop"][key] = value
                with tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(ReleaseProfileError):
                        load_release_profile(self._write_profile(profile, tmp))

    def test_profile_rejects_corresponding_source_drift(self) -> None:
        mutations = (
            ("url", "http://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz"),
            ("sha256", "A" * 64),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                profile = load_release_profile(DEFAULT_PROFILE)
                profile["media"]["corresponding_source"][key] = value
                with tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(ReleaseProfileError):
                        load_release_profile(self._write_profile(profile, tmp))

    def test_profile_requires_corresponding_source(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        del profile["media"]["corresponding_source"]
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

    def test_profile_requires_and_validates_nsis_corresponding_source(self) -> None:
        profile = load_release_profile(DEFAULT_PROFILE)
        del profile["build_tools"]["nsis"]["corresponding_source"]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ReleaseProfileError):
                load_release_profile(self._write_profile(profile, tmp))

        mutations = (
            ("url", "http://downloads.sourceforge.net/project/nsis/NSIS%203/3.12/nsis-3.12-src.tar.bz2"),
            ("sha256", "A" * 64),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                profile = load_release_profile(DEFAULT_PROFILE)
                profile["build_tools"]["nsis"]["corresponding_source"][key] = value
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
