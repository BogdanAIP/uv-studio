from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_MODULE_PATH = ROOT / "tools" / "vendor_videoclaw.py"
VENDOR_SPEC = importlib.util.spec_from_file_location("vendor_videoclaw", VENDOR_MODULE_PATH)
assert VENDOR_SPEC and VENDOR_SPEC.loader
vendor_videoclaw = importlib.util.module_from_spec(VENDOR_SPEC)
sys.modules[VENDOR_SPEC.name] = vendor_videoclaw
VENDOR_SPEC.loader.exec_module(vendor_videoclaw)

RETIRED_PATHS = (
    ".github/workflows/promote-frontend.yml",
    "tools/promote_frontend.py",
    "tests/test_promote_frontend.py",
    "frontend/components/WorkflowPanel.tsx",
    "frontend/components/HomePage.tsx",
    "frontend/components/TopBar.tsx",
    "frontend/components/BrandHeader.tsx",
    "frontend/components/pipelines/PipelinePage.tsx",
    "frontend/components/Sandbox/Sandbox.tsx",
    "frontend/components/stages",
    "frontend/lib/workflowApi.ts",
)

SUPPORTED_ROUTES = (
    "frontend/app/projects/page.tsx",
    "frontend/app/projects/[projectId]/page.tsx",
    "frontend/app/projects/[projectId]/studio/page.tsx",
    "frontend/app/settings/page.tsx",
)


class DonorUiRetirementTests(unittest.TestCase):
    def test_retired_donor_paths_are_absent(self) -> None:
        for relative in RETIRED_PATHS:
            with self.subTest(path=relative):
                self.assertFalse((ROOT / relative).exists())

    def test_supported_routes_remain_present(self) -> None:
        for relative in SUPPORTED_ROUTES:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_frontend_has_no_workflow_api_caller(self) -> None:
        offenders: list[str] = []
        for suffix in ("*.ts", "*.tsx", "*.js", "*.jsx"):
            for path in (ROOT / "frontend").rglob(suffix):
                if "workflowApi" in path.read_text(encoding="utf-8"):
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_supported_tooling_has_no_donor_promotion_entrypoint(self) -> None:
        token = "promote_" + "frontend.py"
        offenders: list[str] = []
        roots = (
            ROOT / ".github" / "workflows",
            ROOT / "tools",
            ROOT / "scripts",
            ROOT / "tests",
        )
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path == Path(__file__).resolve():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if token in text:
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_vendor_tool_rejects_product_frontend_destination(self) -> None:
        for destination in (ROOT / "frontend", ROOT / "frontend" / "nested"):
            with self.subTest(destination=destination):
                with self.assertRaises(vendor_videoclaw.VendorError):
                    vendor_videoclaw.safe_destination(destination)

    def test_settings_model_registry_uses_focused_models_client(self) -> None:
        registry = (ROOT / "frontend" / "lib" / "modelRegistry.ts").read_text(encoding="utf-8")
        client = (ROOT / "frontend" / "lib" / "modelsApi.ts").read_text(encoding="utf-8")
        self.assertIn("from '@/lib/modelsApi'", registry)
        self.assertNotIn("workflowApi", registry)
        self.assertIn("fetch(`/api/models${suffix}`)", client)
        self.assertIn("verified_only", client)


if __name__ == "__main__":
    unittest.main()
