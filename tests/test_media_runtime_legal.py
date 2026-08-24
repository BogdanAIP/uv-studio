from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.media_runtime_closure import exact_closure_carrier_pe_files
from tools.media_runtime_legal import (
    MediaRuntimeLegalError,
    load_and_validate_manifest,
    stage_media_runtime_legal_bundle,
    verify_staged_media_runtime,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_MANIFEST = (
    ROOT / "packaging" / "media-runtime-components.windows-x86_64.json"
)


def _source() -> dict[str, object]:
    return {
        "status": "complete",
        "kind": "archive",
        "upstream": {
            "url": "https://example.invalid/source.tar.xz",
            "sha256": "a" * 64,
        },
    }


def _manifest(files_by_component: dict[str, list[str]]) -> dict[str, object]:
    components = []
    for component_id, files in files_by_component.items():
        components.append(
            {
                "id": component_id,
                "name": component_id,
                "version": "1",
                "license_expression": "MIT",
                "version_evidence": "fixture",
                "files": files,
                "source": _source(),
            }
        )
    return {
        "schema_version": 1,
        "platform": "windows-x86_64",
        "expected_pe_file_count": sum(len(v) for v in files_by_component.values()),
        "release_gate": {"require_all_sources_complete": True},
        "components": components,
    }


class MediaRuntimeLegalTests(unittest.TestCase):
    def test_production_manifest_exactly_covers_audited_carrier_pe_closure(self) -> None:
        expected = [f"Shotcut/{path}" for path in exact_closure_carrier_pe_files()]
        _, summary = load_and_validate_manifest(
            PRODUCTION_MANIFEST, expected_pe_files=expected
        )
        self.assertEqual(summary["pe_file_count"], 52)
        self.assertTrue(summary["all_sources_complete"])
        self.assertEqual(summary["pending_source_components"], [])

    def test_duplicate_or_unmapped_pe_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / "media"
            (media / "Carrier").mkdir(parents=True)
            (media / "Carrier" / "tool.exe").write_bytes(b"pe")
            (media / "Carrier" / "extra.dll").write_bytes(b"pe")
            manifest = root / "components.json"
            manifest.write_text(
                json.dumps(_manifest({"tool": ["Carrier/tool.exe"]})),
                encoding="utf-8",
            )
            with self.assertRaises(MediaRuntimeLegalError):
                verify_staged_media_runtime(media, manifest)

            duplicate = _manifest(
                {"one": ["Carrier/tool.exe"], "two": ["Carrier/tool.exe"]}
            )
            duplicate["expected_pe_file_count"] = 1
            manifest.write_text(json.dumps(duplicate), encoding="utf-8")
            with self.assertRaises(MediaRuntimeLegalError):
                load_and_validate_manifest(manifest)

    def test_pending_source_rejected_when_release_gate_requires_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "components.json"
            raw = _manifest({"tool": ["Carrier/tool.exe"]})
            raw["components"][0]["source"] = {"status": "pending"}
            manifest.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(MediaRuntimeLegalError):
                load_and_validate_manifest(manifest)

    def test_stage_bundle_copies_manifest_and_notice_after_exact_media_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release"
            media = release / "runtime" / "media"
            carrier = media / "Carrier"
            carrier.mkdir(parents=True)
            (carrier / "tool.exe").write_bytes(b"pe")
            (carrier / "codec.dll").write_bytes(b"pe")
            manifest = root / "components.json"
            manifest.write_text(
                json.dumps(
                    _manifest(
                        {
                            "tool": ["Carrier/tool.exe"],
                            "codec": ["Carrier/codec.dll"],
                        }
                    )
                ),
                encoding="utf-8",
            )
            notice = root / "NOTICE.md"
            notice.write_text("# notice\n", encoding="utf-8")

            result = stage_media_runtime_legal_bundle(
                release_root=release,
                media_root=media,
                manifest_file=manifest,
                notice_file=notice,
            )

            self.assertEqual(result["pe_file_count"], 2)
            self.assertTrue(
                (release / "legal" / "media-runtime" / "components.windows-x86_64.json").is_file()
            )
            self.assertTrue(
                (release / "legal" / "media-runtime" / "NOTICE.md").is_file()
            )

    def test_component_paths_reject_traversal_and_backslashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "components.json"
            for bad in ("../evil.dll", r"Carrier\tool.exe"):
                raw = _manifest({"tool": [bad]})
                manifest.write_text(json.dumps(raw), encoding="utf-8")
                with self.assertRaises(MediaRuntimeLegalError):
                    load_and_validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
