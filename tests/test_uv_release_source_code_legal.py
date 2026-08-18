from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.uv_release import (
    _EXPECTED_FRONTEND_NODE_LOCK,
    _EXPECTED_SOURCE_CODE_COMPONENTS,
    _stage_source_code_legal_before_manifest,
)
from uv_studio.release_manifest import ReleaseManifestError


_RESULT = {
    "ok": True,
    "component_count": 2,
    "manifest": "legal/source-code/components.windows-x86_64.json",
}


class ReleaseSourceCodeLegalGateTests(unittest.TestCase):
    def test_gate_is_inactive_without_validated_release_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_stage_source_code_legal_before_manifest(Path(tmp)))

    def test_gate_rejects_unexpected_release_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"UV_NODE_LOCK": "frontend/other-lock.json"},
            clear=True,
        ):
            with self.assertRaises(ReleaseManifestError):
                _stage_source_code_legal_before_manifest(Path(tmp))

    def test_gate_stages_exact_two_donor_components(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"UV_NODE_LOCK": _EXPECTED_FRONTEND_NODE_LOCK},
            clear=True,
        ), patch(
            "tools.source_code_legal.stage_source_code_legal",
            return_value=dict(_RESULT),
        ) as collector:
            root = Path(tmp)
            result = _stage_source_code_legal_before_manifest(root)
            self.assertEqual(result, _RESULT)
            collector.assert_called_once_with(output_root=root)
            self.assertEqual(_EXPECTED_SOURCE_CODE_COMPONENTS, 2)

    def test_gate_rejects_component_count_drift_and_removes_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"UV_NODE_LOCK": _EXPECTED_FRONTEND_NODE_LOCK},
            clear=True,
        ):
            root = Path(tmp)
            legal_root = root / "legal" / "source-code"

            def fake_collector(**_: object) -> dict[str, object]:
                legal_root.mkdir(parents=True)
                (legal_root / "partial.txt").write_text("partial", encoding="utf-8")
                return {
                    "ok": True,
                    "component_count": 3,
                    "manifest": "legal/source-code/components.windows-x86_64.json",
                }

            with patch(
                "tools.source_code_legal.stage_source_code_legal",
                side_effect=fake_collector,
            ):
                with self.assertRaisesRegex(ReleaseManifestError, "component count drifted"):
                    _stage_source_code_legal_before_manifest(root)
            self.assertFalse(legal_root.exists())


if __name__ == "__main__":
    unittest.main()
