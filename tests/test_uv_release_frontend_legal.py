from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.uv_release import (
    _EXPECTED_FRONTEND_NODE_LOCK,
    _stage_frontend_legal_before_manifest,
)
from uv_studio.release_manifest import ReleaseManifestError


_EXACT_RESULT = {
    "ok": True,
    "direct_package_count": 12,
    "direct_license_fallback_count": 2,
    "next_compiled_package_count": 53,
    "next_compiled_override_count": 1,
    "next_compiled_missing_license_expression_count": 0,
    "license_bytes": 123,
    "manifest": "legal/frontend-runtime/components.windows-x86_64.json",
}


class ReleaseFrontendLegalGateTests(unittest.TestCase):
    def test_gate_is_inactive_without_validated_release_profile_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            root = Path(tmp)
            self.assertIsNone(_stage_frontend_legal_before_manifest(root))
            self.assertFalse((root / "legal" / "frontend-runtime").exists())

    def test_gate_rejects_unexpected_node_lock_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"UV_NODE_LOCK": "frontend/other-lock.json"},
            clear=True,
        ):
            with self.assertRaises(ReleaseManifestError):
                _stage_frontend_legal_before_manifest(Path(tmp))

    def test_gate_accepts_only_exact_proven_frontend_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"UV_NODE_LOCK": _EXPECTED_FRONTEND_NODE_LOCK},
            clear=True,
        ), patch(
            "tools.frontend_runtime_legal.stage_frontend_runtime_legal_bundle",
            return_value=dict(_EXACT_RESULT),
        ) as collector:
            root = Path(tmp)
            result = _stage_frontend_legal_before_manifest(root)
            self.assertEqual(result, _EXACT_RESULT)
            collector.assert_called_once()
            kwargs = collector.call_args.kwargs
            self.assertEqual(kwargs["release_root"], root)
            self.assertEqual(kwargs["staged_frontend_root"], root / "frontend")
            self.assertTrue(kwargs["require_compiled_license_expressions"])

    def test_gate_fails_closed_when_any_proven_count_drifts(self) -> None:
        keys = (
            "direct_package_count",
            "direct_license_fallback_count",
            "next_compiled_package_count",
            "next_compiled_override_count",
            "next_compiled_missing_license_expression_count",
        )
        for key in keys:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp, patch.dict(
                os.environ,
                {"UV_NODE_LOCK": _EXPECTED_FRONTEND_NODE_LOCK},
                clear=True,
            ):
                root = Path(tmp)
                legal_root = root / "legal" / "frontend-runtime"

                def fake_collector(**_: object) -> dict[str, object]:
                    legal_root.mkdir(parents=True)
                    (legal_root / "partial.txt").write_text("partial", encoding="utf-8")
                    result = dict(_EXACT_RESULT)
                    result[key] = 99
                    return result

                with patch(
                    "tools.frontend_runtime_legal.stage_frontend_runtime_legal_bundle",
                    side_effect=fake_collector,
                ):
                    with self.assertRaises(ReleaseManifestError):
                        _stage_frontend_legal_before_manifest(root)
                self.assertFalse(legal_root.exists())


if __name__ == "__main__":
    unittest.main()
