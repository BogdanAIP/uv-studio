from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.uv_release import _EXPECTED_NSIS_VERSION, _stage_nsis_legal_before_manifest
from uv_studio.release_manifest import ReleaseManifestError


_SOURCE_URL = "https://downloads.sourceforge.net/project/nsis/NSIS%203/3.12/nsis-3.12-src.tar.bz2"
_SOURCE_SHA = "f3ed7a8e4aa2cf4e8cf47d3b563a02559e0cb4934db2662b2f9661b824e2b186"
_RESULT = {
    "ok": True,
    "component": "nsis-generated-installer-stub",
    "version": "3.12",
    "source_url": _SOURCE_URL,
    "source_archive_bytes": 1818389,
    "source_archive_sha256": _SOURCE_SHA,
    "expected_sha256_enforced": True,
    "copying_path": "legal/nsis/COPYING.txt",
    "copying_bytes": 15632,
    "copying_sha256": "388357c1215ff403c5ebde3a5ecd273e68f8b79a579996775245d1ee65442aba",
}


class ReleaseNSISLegalGateTests(unittest.TestCase):
    def test_gate_is_inactive_without_release_profile_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_stage_nsis_legal_before_manifest(Path(tmp)))

    def test_gate_rejects_partial_or_wrong_version_markers(self) -> None:
        cases = (
            {"UV_NSIS_VERSION": _EXPECTED_NSIS_VERSION},
            {
                "UV_NSIS_VERSION": "3.11",
                "UV_NSIS_SOURCE_URL": _SOURCE_URL,
                "UV_NSIS_SOURCE_SHA256": _SOURCE_SHA,
            },
        )
        for env in cases:
            with self.subTest(env=env), tempfile.TemporaryDirectory() as tmp, patch.dict(
                os.environ, env, clear=True
            ):
                with self.assertRaises(ReleaseManifestError):
                    _stage_nsis_legal_before_manifest(Path(tmp))

    def test_gate_passes_pinned_source_identity_to_nsis_collector(self) -> None:
        env = {
            "UV_NSIS_VERSION": _EXPECTED_NSIS_VERSION,
            "UV_NSIS_SOURCE_URL": _SOURCE_URL,
            "UV_NSIS_SOURCE_SHA256": _SOURCE_SHA,
        }
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, env, clear=True), patch(
            "tools.nsis_runtime_legal.stage_nsis_legal", return_value=dict(_RESULT)
        ) as collector:
            root = Path(tmp)
            result = _stage_nsis_legal_before_manifest(root)
            self.assertEqual(result, _RESULT)
            collector.assert_called_once_with(
                output_root=root,
                version="3.12",
                source_url=_SOURCE_URL,
                expected_sha256=_SOURCE_SHA,
            )

    def test_gate_rejects_collector_that_did_not_enforce_exact_hash(self) -> None:
        env = {
            "UV_NSIS_VERSION": _EXPECTED_NSIS_VERSION,
            "UV_NSIS_SOURCE_URL": _SOURCE_URL,
            "UV_NSIS_SOURCE_SHA256": _SOURCE_SHA,
        }
        for field, value in (
            ("expected_sha256_enforced", False),
            ("source_archive_sha256", "0" * 64),
            ("version", "3.11"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp, patch.dict(
                os.environ, env, clear=True
            ):
                root = Path(tmp)
                legal_root = root / "legal" / "nsis"

                def fake_collector(**_: object) -> dict[str, object]:
                    legal_root.mkdir(parents=True)
                    (legal_root / "partial.txt").write_text("partial", encoding="utf-8")
                    result = dict(_RESULT)
                    result[field] = value
                    return result

                with patch(
                    "tools.nsis_runtime_legal.stage_nsis_legal",
                    side_effect=fake_collector,
                ):
                    with self.assertRaises(ReleaseManifestError):
                        _stage_nsis_legal_before_manifest(root)
                self.assertFalse(legal_root.exists())


if __name__ == "__main__":
    unittest.main()
