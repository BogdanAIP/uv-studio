from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.media_runtime_license_files import load_and_validate_license_manifest

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "packaging" / "media-runtime-components.windows-x86_64.json"
LICENSES = ROOT / "packaging" / "media-runtime-license-files.windows-x86_64.json"


class MediaRuntimeLicenseAcceptanceTests(unittest.TestCase):
    def test_production_license_assets_are_fully_pinned(self) -> None:
        raw, summary = load_and_validate_license_manifest(
            LICENSES, component_manifest_file=COMPONENTS
        )
        self.assertTrue(raw["release_gate"]["require_hashes"])
        self.assertTrue(summary["all_hashes_pinned"])
        self.assertEqual(summary["unpinned_assets"], [])
        self.assertEqual(summary["component_count"], 28)
        self.assertEqual(summary["asset_count"], 27)

    def test_liblzma_is_scoped_to_0bsd_not_unrelated_xz_utilities(self) -> None:
        components = json.loads(COMPONENTS.read_text(encoding="utf-8"))["components"]
        xz = next(item for item in components if item["id"] == "xz-liblzma")
        self.assertEqual(xz["license_expression"], "0BSD")

        assets = json.loads(LICENSES.read_text(encoding="utf-8"))["assets"]
        by_id = {item["id"]: item for item in assets}
        self.assertNotIn("xz-liblzma", by_id["gpl-2.0"]["components"])
        self.assertNotIn("xz-liblzma", by_id["lgpl-2.1"]["components"])
        self.assertIn("xz-liblzma", by_id["xz-copying"]["components"])
        self.assertIn("xz-liblzma", by_id["xz-0bsd"]["components"])


if __name__ == "__main__":
    unittest.main()
