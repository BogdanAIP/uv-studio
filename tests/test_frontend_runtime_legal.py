from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.frontend_runtime_legal import (
    FrontendRuntimeLegalError,
    stage_frontend_runtime_legal_bundle,
)


def _package(root: Path, relative: str, *, name: str, version: str, license_expression: str | None, license_file: bool = False) -> Path:
    package_root = root.joinpath(*relative.split("/"))
    package_root.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {"name": name, "version": version}
    if license_expression is not None:
        data["license"] = license_expression
    (package_root / "package.json").write_text(json.dumps(data), encoding="utf-8")
    if license_file:
        (package_root / "LICENSE").write_text(f"license for {name}\n", encoding="utf-8")
    return package_root


class FrontendRuntimeLegalTests(unittest.TestCase):
    def test_exact_standalone_inventory_and_source_license_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            staged = root / "staged"
            source = root / "frontend"
            release.mkdir()

            _package(staged, "node_modules/react", name="react", version="19.2.5", license_expression="MIT")
            next_root = _package(staged, "node_modules/next", name="next", version="16.3.0", license_expression="MIT")
            _package(source, "node_modules/react", name="react", version="19.2.5", license_expression="MIT", license_file=True)
            _package(source, "node_modules/next", name="next", version="16.3.0", license_expression="MIT", license_file=True)

            compiled = next_root / "dist" / "compiled" / "demo"
            compiled.mkdir(parents=True)
            (compiled / "package.json").write_text(
                json.dumps({"name": "demo", "version": "1.0.0", "license": "ISC"}),
                encoding="utf-8",
            )

            result = stage_frontend_runtime_legal_bundle(
                release_root=release,
                staged_frontend_root=staged,
                source_frontend_root=source,
                require_compiled_license_expressions=True,
            )
            self.assertEqual(result["direct_package_count"], 2)
            self.assertEqual(result["next_compiled_package_count"], 1)
            self.assertEqual(result["next_compiled_missing_license_expression_count"], 0)

            manifest = json.loads(
                (release / "legal" / "frontend-runtime" / "components.windows-x86_64.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual({item["name"] for item in manifest["direct_packages"]}, {"next", "react"})
            self.assertEqual(manifest["next_compiled_packages"][0]["name"], "demo")
            for component in manifest["direct_packages"]:
                self.assertTrue(component["license_files"])
                for item in component["license_files"]:
                    self.assertTrue((release / item["path"]).is_file())
                    self.assertEqual(len(item["sha256"]), 64)

    def test_scoped_package_is_one_direct_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            staged = root / "staged"
            source = root / "frontend"
            release.mkdir()
            _package(
                staged,
                "node_modules/@scope/pkg",
                name="@scope/pkg",
                version="2.0.0",
                license_expression="Apache-2.0",
            )
            _package(
                source,
                "node_modules/@scope/pkg",
                name="@scope/pkg",
                version="2.0.0",
                license_expression="Apache-2.0",
                license_file=True,
            )
            result = stage_frontend_runtime_legal_bundle(
                release_root=release,
                staged_frontend_root=staged,
                source_frontend_root=source,
            )
            self.assertEqual(result["direct_package_count"], 1)

    def test_source_identity_or_missing_direct_license_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for case in ("version", "license"):
                release = root / f"release-{case}"
                staged = root / f"staged-{case}"
                source = root / f"source-{case}"
                release.mkdir()
                _package(staged, "node_modules/demo", name="demo", version="1.0.0", license_expression="MIT")
                _package(
                    source,
                    "node_modules/demo",
                    name="demo",
                    version="2.0.0" if case == "version" else "1.0.0",
                    license_expression="MIT",
                    license_file=case != "license",
                )
                with self.assertRaises(FrontendRuntimeLegalError):
                    stage_frontend_runtime_legal_bundle(
                        release_root=release,
                        staged_frontend_root=staged,
                        source_frontend_root=source,
                    )
                self.assertFalse((release / "legal" / "frontend-runtime").exists())

    def test_compiled_missing_expression_is_reported_or_strictly_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for strict in (False, True):
                release = root / f"release-{strict}"
                staged = root / f"staged-{strict}"
                source = root / f"source-{strict}"
                release.mkdir()
                next_root = _package(staged, "node_modules/next", name="next", version="16.3.0", license_expression="MIT")
                _package(source, "node_modules/next", name="next", version="16.3.0", license_expression="MIT", license_file=True)
                compiled = next_root / "dist" / "compiled" / "busboy"
                compiled.mkdir(parents=True)
                (compiled / "package.json").write_text(json.dumps({"name": "busboy"}), encoding="utf-8")

                if strict:
                    with self.assertRaises(FrontendRuntimeLegalError):
                        stage_frontend_runtime_legal_bundle(
                            release_root=release,
                            staged_frontend_root=staged,
                            source_frontend_root=source,
                            require_compiled_license_expressions=True,
                        )
                    self.assertFalse((release / "legal" / "frontend-runtime").exists())
                else:
                    result = stage_frontend_runtime_legal_bundle(
                        release_root=release,
                        staged_frontend_root=staged,
                        source_frontend_root=source,
                    )
                    self.assertEqual(result["next_compiled_missing_license_expression_count"], 1)


if __name__ == "__main__":
    unittest.main()
