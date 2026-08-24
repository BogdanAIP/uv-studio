from __future__ import annotations

import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from tools.python_runtime_legal import (
    PythonRuntimeLegalError,
    parse_exact_lock,
    stage_python_runtime_legal_bundle,
)


class _FakeDistribution:
    def __init__(self, root: Path, name: str, version: str, *, with_license: bool = True) -> None:
        self._root = root
        self.version = version
        self.name = name
        self.metadata = Message()
        self.metadata["Name"] = name
        self.metadata["Version"] = version
        self.metadata["License-Expression"] = "MIT"
        self.files = []
        if with_license:
            relative = Path(f"{name}-{version}.dist-info/licenses/LICENSE.txt")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"license for {name}\n", encoding="utf-8")
            self.files = [relative]
            self.metadata["License-File"] = "LICENSE.txt"

    def locate_file(self, file: object) -> Path:
        return self._root / Path(str(file))


class PythonRuntimeLegalTests(unittest.TestCase):
    def test_production_lock_is_exact_and_has_expected_shipping_count(self) -> None:
        root = Path(__file__).resolve().parents[1]
        locked = parse_exact_lock(root / "requirements-uv-release-win-x86_64.txt")
        self.assertEqual(len(locked), 32)
        self.assertEqual(locked["fastapi"][1], "0.141.1")
        self.assertEqual(locked["pywin32"][1], "312")

    def test_lock_rejects_ranges_duplicates_and_unpinned_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "lock.txt"
            for text in (
                "one>=1\n",
                "one\n",
                "one==1\none==1\n",
                "-r other.txt\n",
            ):
                lock.write_text(text, encoding="utf-8")
                with self.assertRaises(PythonRuntimeLegalError):
                    parse_exact_lock(lock)

    def test_stage_bundle_covers_exact_lock_cpython_and_pyinstaller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            release.mkdir()
            lock = root / "lock.txt"
            lock.write_text("demo-pkg==1.2.3\n", encoding="utf-8")
            python_license = root / "PYTHON-LICENSE.txt"
            python_license.write_text("PSF license\n", encoding="utf-8")
            site = root / "site"
            demo = _FakeDistribution(site, "demo-pkg", "1.2.3")
            freezer = _FakeDistribution(site, "pyinstaller", "6.21.0")

            def distribution(name: str) -> _FakeDistribution:
                if name == "demo-pkg":
                    return demo
                if name == "pyinstaller":
                    return freezer
                raise AssertionError(name)

            with patch("tools.python_runtime_legal.metadata.distribution", side_effect=distribution):
                result = stage_python_runtime_legal_bundle(
                    release_root=release,
                    lock_file=lock,
                    pyinstaller_version="6.21.0",
                    python_license_file=python_license,
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["shipping_distribution_count"], 1)
            self.assertEqual(result["component_count"], 3)
            manifest = json.loads(
                (release / "legal" / "python-runtime" / "components.windows-x86_64.json").read_text(
                    encoding="utf-8"
                )
            )
            ids = {item["id"] for item in manifest["components"]}
            self.assertEqual(ids, {"cpython-runtime", "demo-pkg", "pyinstaller"})
            for component in manifest["components"]:
                self.assertTrue(component["license_files"])
                for item in component["license_files"]:
                    target = release / item["path"]
                    self.assertTrue(target.is_file())
                    self.assertEqual(len(item["sha256"]), 64)

    def test_version_mismatch_missing_license_and_stale_output_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / "lock.txt"
            lock.write_text("demo==1.0\n", encoding="utf-8")
            python_license = root / "PYTHON-LICENSE.txt"
            python_license.write_text("PSF license\n", encoding="utf-8")
            site = root / "site"
            freezer = _FakeDistribution(site, "pyinstaller", "6.21.0")

            for demo in (
                _FakeDistribution(site, "demo", "2.0"),
                _FakeDistribution(site, "demo", "1.0", with_license=False),
            ):
                release = root / f"release-{demo.version}-{len(demo.files)}"
                release.mkdir()

                def distribution(name: str) -> _FakeDistribution:
                    return demo if name == "demo" else freezer

                with patch("tools.python_runtime_legal.metadata.distribution", side_effect=distribution):
                    with self.assertRaises(PythonRuntimeLegalError):
                        stage_python_runtime_legal_bundle(
                            release_root=release,
                            lock_file=lock,
                            pyinstaller_version="6.21.0",
                            python_license_file=python_license,
                        )
                self.assertFalse((release / "legal" / "python-runtime").exists())

            release = root / "stale-release"
            stale = release / "legal" / "python-runtime"
            stale.mkdir(parents=True)
            with self.assertRaises(PythonRuntimeLegalError):
                stage_python_runtime_legal_bundle(
                    release_root=release,
                    lock_file=lock,
                    pyinstaller_version="6.21.0",
                    python_license_file=python_license,
                )


if __name__ == "__main__":
    unittest.main()
