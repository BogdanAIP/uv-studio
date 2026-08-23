"""Browser evidence for the preparation-only Product Orchestrator Commercial journey."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from test_user_outcomes import (
    BACKEND_ORIGIN,
    FRONTEND,
    FRONTEND_ORIGIN,
    ROOT,
    _api_json,
    _project_path,
    _run,
    _start_process,
    _wait_http,
)


def _image_fixture(path: Path) -> None:
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=orange:s=640x360:d=0.04",
        "-frames:v", "1", "-update", "1", str(path),
    ])


class CommercialProductBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None:
            raise unittest.SkipTest("Commercial browser E2E requires FFmpeg for the image fixture")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("Commercial browser E2E requires npm")
        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-commercial-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)
        cls.image = cls.temp_root / "product-frame.png"
        _image_fixture(cls.image)
        env = os.environ.copy()
        env.update({
            "PYTHONUNBUFFERED": "1",
            "NEXT_TELEMETRY_DISABLED": "1",
            "UV_STUDIO_PROJECTS_DIR": str(cls.temp_root / "projects"),
            "UV_STUDIO_CONFIG_DIR": str(cls.temp_root / "config"),
        })
        cls.backend = _start_process(
            [sys.executable, "-m", "uv_studio.server"], cwd=ROOT, env=env,
            log_path=cls.artifact_dir / "commercial-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND, env=env,
                log_path=cls.artifact_dir / "commercial-frontend.log",
            )
            _wait_http(f"{FRONTEND_ORIGIN}/projects", cls.frontend)
        except Exception:
            cls.backend.stop()
            cls._tmp.cleanup()
            raise
        cls._playwright = sync_playwright().start()
        try:
            cls.browser = cls._playwright.chromium.launch(headless=True)
        except Exception:
            cls.frontend.stop()
            cls.backend.stop()
            cls._playwright.stop()
            cls._tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "browser"):
            cls.browser.close()
        if hasattr(cls, "_playwright"):
            cls._playwright.stop()
        if hasattr(cls, "frontend"):
            cls.frontend.stop()
        if hasattr(cls, "backend"):
            cls.backend.stop()
        if hasattr(cls, "_tmp"):
            cls._tmp.cleanup()

    def _new_page(self) -> Page:
        context = self.browser.new_context(
            base_url=FRONTEND_ORIGIN,
            viewport={"width": 1600, "height": 1200},
            locale="ru-RU",
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(60_000)
        return page

    def test_commercial_workspace_reaches_truthful_preparation_state_from_visible_inputs(self) -> None:
        page = self._new_page()
        title = "Commercial E2E"
        project = _api_json("POST", "/api/uv/projects", {"title": title, "recipe_id": "commercial_product"})
        project_id = project["project_id"]
        encoded = urllib.parse.quote(project_id, safe="")

        page.goto(f"/projects/{encoded}")
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Продуктовое рабочее пространство", exact=True)).to_be_visible()
        expect(page.get_by_text("Нужна подготовка", exact=True)).to_be_visible()
        page.get_by_label("Stage 8 brief").fill("Показать новую упаковку и сохранить точные детали продукта")
        page.get_by_label("Stage 8 script").fill("Крупный план упаковки. Польза. Финальный packshot.")
        page.locator('input[aria-label="Stage 8 workspace image"]').set_input_files(str(self.image))
        expect(page.get_by_label(f"Использовать {self.image.name}")).to_be_checked(timeout=60_000)
        page.get_by_role("button", name="Сохранить рабочее пространство", exact=True).click()
        expect(
            page.get_by_text(
                "Рабочее пространство сохранено с точной SHA-привязкой выбранных материалов.",
                exact=True,
            )
        ).to_be_visible(timeout=60_000)
        expect(page.get_by_text("Готово к следующему действию", exact=True)).to_be_visible(timeout=60_000)
        expect(page.get_by_role("button", name="Собрать обычный видеоролик", exact=True)).to_have_count(0)

        workflow = _api_json("GET", _project_path(project_id, "/workflow"))
        self.assertEqual(workflow["recipe_id"], "commercial_product")
        self.assertEqual(workflow["readiness"], "ready")
        self.assertEqual(
            [item["workspace_id"] for item in workflow["relevant_workspaces"]],
            ["commercial_product"],
        )
        self.assertEqual(workflow["next_actions"], [])
        self.assertIsNone(workflow["current_outcome"])
        codes = {item["code"] for item in workflow["diagnostics"]}
        self.assertNotIn("workflow_not_migrated", codes)
        self.assertIn("commercial_required_gates_not_authoritative", codes)
        self.assertIn("commercial_final_render_not_authoritative", codes)
        page.screenshot(path=str(self.artifact_dir / "commercial-outcome.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()
