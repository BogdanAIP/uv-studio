"""First-run product UX checks for the installed/browser product surface."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

import test_user_outcomes as harness


class FirstRunProductUXOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or "npm"
        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-studio-first-run-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(harness.ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update(
            {
                "PYTHONUNBUFFERED": "1",
                "NEXT_TELEMETRY_DISABLED": "1",
                "UV_STUDIO_PROJECTS_DIR": str(cls.temp_root / "projects"),
                "UV_STUDIO_CONFIG_DIR": str(cls.temp_root / "config"),
            }
        )

        cls.backend = harness._start_process(
            [sys.executable, "-m", "uv_studio.server"],
            cwd=harness.ROOT,
            env=env,
            log_path=cls.artifact_dir / "first-run-backend.log",
        )
        try:
            harness._wait_http(f"{harness.BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = harness._start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=harness.FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "first-run-frontend.log",
            )
            harness._wait_http(f"{harness.FRONTEND_ORIGIN}/projects", cls.frontend)
            cls._playwright = sync_playwright().start()
            cls.browser = cls._playwright.chromium.launch(headless=True)
        except Exception:
            cls.backend.stop()
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
        cls.backend.stop()
        cls._tmp.cleanup()

    def test_first_run_can_create_project_and_controls_are_dark(self) -> None:
        page = self.browser.new_page()
        try:
            page.goto(f"{harness.FRONTEND_ORIGIN}/projects")
            expect(page.get_by_role("heading", name="Проекты", exact=True)).to_be_visible()

            name_input = page.get_by_placeholder("Название проекта (необязательно)")
            create_button = page.get_by_role("button", name="Создать проект", exact=True)
            expect(name_input).to_be_visible()
            expect(create_button).to_be_enabled()
            expect(name_input).to_have_css("background-color", "rgb(18, 21, 27)")
            expect(name_input).to_have_css("color", "rgb(244, 244, 245)")

            create_button.click()
            page.wait_for_url("**/projects/*")
            expect(page.get_by_role("heading", name="Новый проект", exact=True)).to_be_visible()

            page.goto(f"{harness.FRONTEND_ORIGIN}/settings")
            model_input = page.get_by_placeholder("например, gpt-5")
            expect(model_input).to_be_visible(timeout=30_000)
            expect(model_input).to_have_css("background-color", "rgb(18, 21, 27)")
            expect(model_input).to_have_css("color", "rgb(244, 244, 245)")

            page.screenshot(
                path=str(self.artifact_dir / "first-run-product-ux.png"),
                full_page=True,
            )
        finally:
            page.close()
