from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.media_runtime_license_files import (
    MediaRuntimeLicenseError,
    load_and_validate_license_manifest,
    stage_media_runtime_license_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_COMPONENT_MANIFEST = (
    ROOT / "packaging" / "media-runtime-components.windows-x86_64.json"
)


def _component_manifest(path: Path, ids: list[str]) -> None:
    components = []
    for index, component_id in enumerate(ids):
        components.append(
            {
                "id": component_id,
                "name": component_id,
                "version": "1",
                "license_expression": "MIT",
                "version_evidence": "fixture",
                "files": [f"Carrier/{component_id}-{index}.dll"],
                "source": {
                    "status": "complete",
                    "kind": "archive",
                    "upstream": {
                        "url": "https://example.invalid/source.tar.xz",
                        "sha256": "a" * 64,
                    },
                },
            }
        )
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "platform": "windows-x86_64",
                "expected_pe_file_count": len(ids),
                "release_gate": {"require_all_sources_complete": True},
                "components": components,
            }
        ),
        encoding="utf-8",
    )


def _license_manifest(path: Path, assets: list[dict[str, object]], *, require_hashes: bool = True) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "platform": "windows-x86_64",
                "purpose": "fixture",
                "release_gate": {
                    "require_hashes": require_hashes,
                    "max_asset_bytes": 1024,
                    "max_total_bytes": 4096,
                },
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )


class MediaRuntimeLicenseFileTests(unittest.TestCase):
    def test_production_license_manifest_covers_every_component(self) -> None:
        manifest = ROOT / "packaging" / "media-runtime-license-files.windows-x86_64.json"
        raw, summary = load_and_validate_license_manifest(
            manifest,
            component_manifest_file=PRODUCTION_COMPONENT_MANIFEST,
        )
        self.assertEqual(summary["component_count"], 28)
        self.assertEqual(summary["asset_count"], 27)
        self.assertIn("assets", raw)

    def test_carrier_assets_stage_with_exact_hash_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            media = release / "runtime" / "media"
            carrier = media / "Carrier"
            carrier.mkdir(parents=True)
            release.mkdir(exist_ok=True)
            data = b"license text\n"
            (carrier / "LICENSE.txt").write_bytes(data)
            components = root / "components.json"
            _component_manifest(components, ["one"])
            licenses = root / "licenses.json"
            _license_manifest(
                licenses,
                [
                    {
                        "id": "one-license",
                        "target": "one-LICENSE.txt",
                        "components": ["one"],
                        "source": {"kind": "carrier", "path": "Carrier/LICENSE.txt"},
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                ],
            )

            result = stage_media_runtime_license_bundle(
                release_root=release,
                media_root=media,
                component_manifest_file=components,
                license_manifest_file=licenses,
            )

            self.assertTrue(result["ok"])
            self.assertTrue(result["all_hashes_pinned"])
            staged = release / "legal" / "media-runtime" / "licenses" / "one-LICENSE.txt"
            self.assertEqual(staged.read_bytes(), data)
            self.assertTrue(
                (release / "legal" / "media-runtime" / "license-files.windows-x86_64.json").is_file()
            )

    def test_hash_mismatch_fails_closed_and_removes_partial_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            media = release / "runtime" / "media"
            carrier = media / "Carrier"
            carrier.mkdir(parents=True)
            release.mkdir(exist_ok=True)
            (carrier / "LICENSE.txt").write_text("actual", encoding="utf-8")
            components = root / "components.json"
            _component_manifest(components, ["one"])
            licenses = root / "licenses.json"
            _license_manifest(
                licenses,
                [
                    {
                        "id": "one-license",
                        "target": "one-LICENSE.txt",
                        "components": ["one"],
                        "source": {"kind": "carrier", "path": "Carrier/LICENSE.txt"},
                        "sha256": "0" * 64,
                    }
                ],
            )
            with self.assertRaises(MediaRuntimeLicenseError):
                stage_media_runtime_license_bundle(
                    release_root=release,
                    media_root=media,
                    component_manifest_file=components,
                    license_manifest_file=licenses,
                )
            self.assertFalse((release / "legal" / "media-runtime" / "licenses").exists())

    def test_missing_component_duplicate_target_and_insecure_url_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            components = root / "components.json"
            _component_manifest(components, ["one", "two"])
            licenses = root / "licenses.json"

            _license_manifest(
                licenses,
                [
                    {
                        "id": "one",
                        "target": "LICENSE.txt",
                        "components": ["one"],
                        "source": {"kind": "url", "url": "https://example.invalid/license"},
                        "sha256": "1" * 64,
                    }
                ],
            )
            with self.assertRaises(MediaRuntimeLicenseError):
                load_and_validate_license_manifest(
                    licenses, component_manifest_file=components
                )

            _license_manifest(
                licenses,
                [
                    {
                        "id": "one",
                        "target": "same.txt",
                        "components": ["one"],
                        "source": {"kind": "url", "url": "https://example.invalid/one"},
                        "sha256": "1" * 64,
                    },
                    {
                        "id": "two",
                        "target": "same.txt",
                        "components": ["two"],
                        "source": {"kind": "url", "url": "https://example.invalid/two"},
                        "sha256": "2" * 64,
                    },
                ],
            )
            with self.assertRaises(MediaRuntimeLicenseError):
                load_and_validate_license_manifest(
                    licenses, component_manifest_file=components
                )

            _license_manifest(
                licenses,
                [
                    {
                        "id": "one",
                        "target": "one.txt",
                        "components": ["one", "two"],
                        "source": {"kind": "url", "url": "http://example.invalid/license"},
                        "sha256": "1" * 64,
                    }
                ],
            )
            with self.assertRaises(MediaRuntimeLicenseError):
                load_and_validate_license_manifest(
                    licenses, component_manifest_file=components
                )

    def test_traversal_and_required_hash_gate_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            components = root / "components.json"
            _component_manifest(components, ["one"])
            licenses = root / "licenses.json"
            for target in ("../escape.txt", r"bad\\path.txt"):
                _license_manifest(
                    licenses,
                    [
                        {
                            "id": "one",
                            "target": target,
                            "components": ["one"],
                            "source": {"kind": "url", "url": "https://example.invalid/license"},
                            "sha256": "1" * 64,
                        }
                    ],
                )
                with self.assertRaises(MediaRuntimeLicenseError):
                    load_and_validate_license_manifest(
                        licenses, component_manifest_file=components
                    )

            _license_manifest(
                licenses,
                [
                    {
                        "id": "one",
                        "target": "one.txt",
                        "components": ["one"],
                        "source": {"kind": "url", "url": "https://example.invalid/license"},
                        "sha256": None,
                    }
                ],
                require_hashes=True,
            )
            with self.assertRaises(MediaRuntimeLicenseError):
                load_and_validate_license_manifest(
                    licenses, component_manifest_file=components
                )


if __name__ == "__main__":
    unittest.main()
