from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_REQUIREMENTS = ROOT / "requirements-uv.txt"
DEV_REQUIREMENTS = ROOT / "requirements-uv-dev.txt"
SETUP_SCRIPT = ROOT / "scripts" / "setup-dev.ps1"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

_PROVIDER_OR_HEAVY_OPTIONAL_PACKAGES = {
    "dashscope",
    "edge-tts",
    "openai",
    "pillow",
    "playwright",
    "pypdf2",
    "python-docx",
    "requests",
}
_REQUIRED_CORE_PACKAGES = {
    "anyio",
    "fastapi",
    "mcp",
    "pydantic",
    "starlette",
    "uvicorn",
}
_NAME_RE = re.compile(r"^([A-Za-z0-9_.-]+)")


def _requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-r "):
            continue
        match = _NAME_RE.match(line)
        if match is None:
            raise AssertionError(f"unsupported requirement line in {path.name}: {raw_line!r}")
        names.add(match.group(1).lower().replace("_", "-"))
    return names


class DependencyContractTests(unittest.TestCase):
    def test_core_requirements_own_direct_uv_runtime_packages(self) -> None:
        names = _requirement_names(CORE_REQUIREMENTS)
        self.assertTrue(_REQUIRED_CORE_PACKAGES.issubset(names), names)

    def test_core_requirements_exclude_provider_and_heavy_optional_packages(self) -> None:
        names = _requirement_names(CORE_REQUIREMENTS)
        self.assertFalse(names.intersection(_PROVIDER_OR_HEAVY_OPTIONAL_PACKAGES), names)

    def test_dev_requirements_layer_on_core_and_add_test_tooling_only(self) -> None:
        text = DEV_REQUIREMENTS.read_text(encoding="utf-8")
        self.assertIn("-r requirements-uv.txt", text)
        names = _requirement_names(DEV_REQUIREMENTS)
        self.assertEqual(names, {"httpx", "playwright"})
        self.assertIn("playwright==1.61.0", text)

    def test_development_setup_does_not_install_vendor_backend_requirements(self) -> None:
        text = SETUP_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("requirements-uv-dev.txt", text)
        self.assertNotIn("vendor/videoclaw-app/backend/requirements.txt", text.replace("\\", "/"))
        self.assertNotIn("BackendRequirements", text)

    def test_ci_does_not_install_vendor_backend_requirements(self) -> None:
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("pip install -r vendor/videoclaw-app/backend/requirements.txt", text)
        self.assertIn("Import UV Studio server from core dependencies", text)
        self.assertIn("Import UV Studio server without vendor dependency installation", text)

    def test_modern_studio_and_media_api_do_not_import_recipe_or_orchestrator_boundaries(self) -> None:
        modern_modules = (
            ROOT / "uv_studio" / "api" / "project_common.py",
            ROOT / "uv_studio" / "api" / "studio_timeline.py",
            ROOT / "uv_studio" / "api" / "project_media.py",
        )
        forbidden = (
            "uv_studio.api.projects",
            "uv_studio.api.recipes",
            "uv_studio.orchestration",
            "uv_studio.recipes",
        )
        for path in modern_modules:
            text = path.read_text(encoding="utf-8")
            for import_path in forbidden:
                self.assertNotIn(import_path, text, f"{path.name} imports {import_path}")

    def test_projects_ui_consumes_backend_owned_identity_projection(self) -> None:
        text = (ROOT / "frontend" / "app" / "projects" / "page.tsx").read_text(encoding="utf-8")
        self.assertIn("project.product_identity", text)
        self.assertNotIn("project.extensions.studio", text)
        self.assertNotIn("project.recipe_id === 'studio_v2'", text)


if __name__ == "__main__":
    unittest.main()
