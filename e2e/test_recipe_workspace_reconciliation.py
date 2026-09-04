"""Browser evidence for modern creation truth and preserved legacy workspace routing."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

from legacy_project_fixture import seed_legacy_project
from test_user_outcomes import (
    BACKEND_ORIGIN,
    FRONTEND,
    FRONTEND_ORIGIN,
    ROOT,
    _api_json,
    _start_process,
    _wait_http,
)


class RecipeWorkspaceReconciliationBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("Recipe reconciliation browser E2E requires npm")
        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-recipe-reconciliation-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.projects_root = cls.temp_root / "projects"
        cls.artifact_dir = Path(os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "PYTHONUNBUFFERED": "1",
            "NEXT_TELEMETRY_DISABLED": "1",
            "UV_STUDIO_PROJECTS_DIR": str(cls.projects_root),
            "UV_STUDIO_CONFIG_DIR": str(cls.temp_root / "config"),
        })
        cls.backend = _start_process(
            [sys.executable, "-m", "uv_studio.server"], cwd=ROOT, env=env,
            log_path=cls.artifact_dir / "recipe-reconciliation-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND, env=env,
                log_path=cls.artifact_dir / "recipe-reconciliation-frontend.log",
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

    def test_creation_catalog_does_not_advertise_preserved_only_recipes(self) -> None:
        page = self._new_page()
        page.goto("/projects")
        expect(page.get_by_role("heading", name="Проекты", exact=True)).to_be_visible()

        for title in ("Перенос движения", "Говорящий персонаж", "Performance / lip-sync"):
            expect(page.get_by_role("button", name=title, exact=False)).to_have_count(0)

        directions = _api_json("GET", "/api/uv/projects/studio/directions")
        direction_ids = {item["direction_id"] for item in directions}
        self.assertTrue(direction_ids)
        self.assertFalse({"action_transfer", "digital_human", "performance_lip_sync"} & direction_ids)

    def test_preserved_unsupported_project_has_no_foreign_workspace_leakage(self) -> None:
        # Import/recovery must continue to support preserved recipe IDs, so seed
        # canonical Project Store compatibility state directly instead of using
        # the deliberately retired recipe-backed new-project HTTP endpoint.
        project_id = seed_legacy_project(
            self.projects_root,
            title="Preserved Action Transfer",
            recipe_id="action_transfer",
        )
        encoded = urllib.parse.quote(project_id, safe="")

        page = self._new_page()
        page.goto(f"/projects/{encoded}")
        expect(page.get_by_role("heading", name="Preserved Action Transfer", exact=True)).to_be_visible()
        expect(page.get_by_text("Сценарий переносится в новый процесс", exact=True)).to_be_visible()
        expect(page.get_by_text("Этот сценарий ещё не перенесён в Product Orchestrator.", exact=True)).to_be_visible()

        expect(page.get_by_role("heading", name="Точечное редактирование исходного видео", exact=True)).to_have_count(0)
        expect(page.get_by_text("Stage 6 · Sequence Continuity", exact=True)).to_have_count(0)
        expect(page.get_by_text("Stage 5 · Dubbing / Translation", exact=True)).to_have_count(0)
        expect(page.get_by_text("Stage 8 · Performance / lip-sync", exact=True)).to_have_count(0)
        expect(page.get_by_role("heading", name="Проект и восстановление", exact=True)).to_be_visible()

        workflow = _api_json("GET", f"/api/uv/projects/{encoded}/workflow")
        self.assertEqual(workflow["readiness"], "partial")
        self.assertEqual(workflow["relevant_workspaces"], [])
        self.assertEqual(workflow["next_actions"], [])
        self.assertIn("workflow_not_migrated", {item["code"] for item in workflow["diagnostics"]})
        page.screenshot(path=str(self.artifact_dir / "recipe-reconciliation-unsupported.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()