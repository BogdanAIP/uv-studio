from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.frontend_runtime_legal import (
    FrontendRuntimeLegalError,
    stage_frontend_runtime_legal_bundle,
)


def _write_package(
    root: Path,
    relative: str,
    *,
    name: str,
    version: str,
    license_expression: str | None,
    extra: dict[str, object] | None = None,
    license_text: str | None = None,
) -> Path:
    package_root = root.joinpath(*relative.split("/"))
    package_root.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {"name": name, "version": version}
    if license_expression is not None:
        data["license"] = license_expression
    if extra:
        data.update(extra)
    (package_root / "package.json").write_text(
        json.dumps(data, separators=(",", ":")),
        encoding="utf-8",
    )
    if license_text is not None:
        (package_root / "LICENSE").write_text(license_text, encoding="utf-8")
    return package_root


def _write_busboy_override(
    root: Path,
    runtime_package_json: Path,
    *,
    next_ref: str = "v16.3.0",
    dependency_version: str = "1.6.0",
) -> Path:
    license_path = root / "packaging" / "frontend-compiled-licenses" / "busboy-1.6.0-LICENSE.txt"
    license_path.parent.mkdir(parents=True, exist_ok=True)
    license_path.write_text("busboy MIT license\n", encoding="utf-8")
    manifest = root / "packaging" / "frontend-compiled-licenses.windows-x86_64.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "platform": "windows-x86_64",
                "overrides": [
                    {
                        "runtime_package_json": "node_modules/next/dist/compiled/busboy/package.json",
                        "runtime_package_json_sha256": hashlib.sha256(
                            runtime_package_json.read_bytes()
                        ).hexdigest(),
                        "name": "busboy",
                        "version": dependency_version,
                        "license_expression": "MIT",
                        "license_file": "packaging/frontend-compiled-licenses/busboy-1.6.0-LICENSE.txt",
                        "license_file_sha256": hashlib.sha256(
                            license_path.read_bytes()
                        ).hexdigest(),
                        "next_recipe": {
                            "repository": "https://github.com/vercel/next.js",
                            "ref": next_ref,
                            "taskfile_path": "packages/next/taskfile.js",
                            "package_path": "packages/next/package.json",
                        },
                        "upstream_license": {
                            "repository": "https://github.com/mscdex/busboy",
                            "ref": "v1.6.0",
                            "path": "LICENSE",
                            "git_blob_sha1": "290762e94f4e2f2b52cc13ae4f2b63ac0269bfd1",
                            "local_copy_normalized": True,
                        },
                    }
                ],
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    return manifest


class FrontendCompiledOverrideTests(unittest.TestCase):
    def _fixture(self, root: Path, *, next_busboy_version: str = "1.6.0") -> tuple[Path, Path, Path, Path]:
        release = root / "release"
        staged = root / "staged"
        source = root / "frontend"
        release.mkdir()
        _write_package(
            staged,
            "node_modules/next",
            name="next",
            version="16.3.0",
            license_expression="MIT",
        )
        _write_package(
            source,
            "node_modules/next",
            name="next",
            version="16.3.0",
            license_expression="MIT",
            extra={"devDependencies": {"busboy": next_busboy_version}},
            license_text="next MIT license\n",
        )
        compiled = staged / "node_modules" / "next" / "dist" / "compiled" / "busboy"
        compiled.mkdir(parents=True)
        runtime_package = compiled / "package.json"
        runtime_package.write_text('{"name":"busboy"}', encoding="utf-8")
        override = _write_busboy_override(root, runtime_package)
        return release, staged, source, override

    def test_busboy_override_closes_strict_compiled_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release, staged, source, override = self._fixture(root)

            result = stage_frontend_runtime_legal_bundle(
                release_root=release,
                staged_frontend_root=staged,
                source_frontend_root=source,
                compiled_overrides_file=override,
                require_compiled_license_expressions=True,
            )

            self.assertEqual(result["next_compiled_override_count"], 1)
            self.assertEqual(result["next_compiled_missing_license_expression_count"], 0)
            manifest = json.loads(
                (
                    release
                    / "legal"
                    / "frontend-runtime"
                    / "components.windows-x86_64.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(
                manifest["next_compiled_override_paths"],
                ["node_modules/next/dist/compiled/busboy/package.json"],
            )
            busboy = next(
                item
                for item in manifest["next_compiled_packages"]
                if item["name"] == "busboy"
            )
            self.assertEqual(busboy["version"], "1.6.0")
            self.assertEqual(busboy["license_expression"], "MIT")
            self.assertEqual(
                busboy["license_source"]["kind"],
                "checked-in-compiled-override",
            )
            staged_license = release / busboy["license_source"]["license_file"]["path"]
            self.assertTrue(staged_license.is_file())

    def test_override_fails_closed_on_runtime_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release, staged, source, override = self._fixture(root)
            runtime_package = (
                staged
                / "node_modules"
                / "next"
                / "dist"
                / "compiled"
                / "busboy"
                / "package.json"
            )
            runtime_package.write_text('{"name":"busboy","changed":true}', encoding="utf-8")

            with self.assertRaises(FrontendRuntimeLegalError):
                stage_frontend_runtime_legal_bundle(
                    release_root=release,
                    staged_frontend_root=staged,
                    source_frontend_root=source,
                    compiled_overrides_file=override,
                    require_compiled_license_expressions=True,
                )
            self.assertFalse((release / "legal" / "frontend-runtime").exists())

    def test_override_fails_closed_when_next_recipe_or_dependency_pin_drifts(self) -> None:
        for case in ("recipe", "dependency"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                release, staged, source, override = self._fixture(
                    root,
                    next_busboy_version="9.9.9" if case == "dependency" else "1.6.0",
                )
                if case == "recipe":
                    data = json.loads(override.read_text(encoding="utf-8"))
                    data["overrides"][0]["next_recipe"]["ref"] = "v16.2.0"
                    override.write_text(
                        json.dumps(data, separators=(",", ":")),
                        encoding="utf-8",
                    )

                with self.assertRaises(FrontendRuntimeLegalError):
                    stage_frontend_runtime_legal_bundle(
                        release_root=release,
                        staged_frontend_root=staged,
                        source_frontend_root=source,
                        compiled_overrides_file=override,
                        require_compiled_license_expressions=True,
                    )
                self.assertFalse((release / "legal" / "frontend-runtime").exists())

    def test_unused_override_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release, staged, source, override = self._fixture(root)
            compiled = staged / "node_modules" / "next" / "dist" / "compiled" / "busboy"
            (compiled / "package.json").unlink()

            with self.assertRaises(FrontendRuntimeLegalError):
                stage_frontend_runtime_legal_bundle(
                    release_root=release,
                    staged_frontend_root=staged,
                    source_frontend_root=source,
                    compiled_overrides_file=override,
                )
            self.assertFalse((release / "legal" / "frontend-runtime").exists())


if __name__ == "__main__":
    unittest.main()
