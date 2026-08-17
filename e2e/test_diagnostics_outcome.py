"""Browser outcome for the Stage 9 product diagnostics and recovery surface."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from e2e.test_user_outcomes import (
    BACKEND_ORIGIN,
    FRONTEND,
    FRONTEND_ORIGIN,
    ROOT,
    _start_process,
    _wait_http,
)


class DiagnosticsBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("diagnostics browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-studio-diagnostics-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update(
            {
                "PYTHONUNBUFFERED": "1",
                "NEXT_TELEMETRY_DISABLED": "1",
                "UV_STUDIO_USER_DATA_DIR": str(cls.temp_root / "user-data"),
                "UV_STUDIO_PROJECTS_DIR": str(cls.temp_root / "projects"),
                "UV_STUDIO_CONFIG_DIR": str(cls.temp_root / "config"),
            }
        )
        cls.backend = _start_process(
            [sys.executable, "-m", "uv_studio.server"],
            cwd=ROOT,
            env=env,
            log_path=artifact_dir / "diagnostics-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=artifact_dir / "diagnostics-frontend.log",
            )
            _wait_http(f"{FRONTEND_ORIGIN}/diagnostics", cls.frontend)
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

    def test_user_can_run_full_secret_safe_self_check(self) -> None:
        context = self.browser.new_context(
            base_url=FRONTEND_ORIGIN,
            viewport={"width": 1440, "height": 1000},
            locale="ru-RU",
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(30_000)

        page.goto("/diagnostics")
        expect(page.get_by_role("heading", name="Диагностика и восстановление", exact=True)).to_be_visible()
        expect(page.get_by_text("Сейчас показана быстрая проверка", exact=False)).to_be_visible()
        expect(page.get_by_text("Project Store", exact=True)).to_be_visible()

        page.get_by_role("button", name="Запустить полную проверку", exact=True).click()
        expect(page.get_by_text("Выполнена полная проверка", exact=False)).to_be_visible(timeout=120_000)
        expect(page.get_by_text("доступна запись", exact=True)).to_have_count(3)
        expect(page.get_by_text("проверено", exact=True)).to_be_visible()

        body = page.locator("body").inner_text()
        self.assertNotIn(str(self.temp_root), body)
        self.assertNotIn("UV_STUDIO_USER_DATA_DIR", body)
        self.assertNotIn("PYTHONPATH", body)


if __name__ == "__main__":
    unittest.main()
