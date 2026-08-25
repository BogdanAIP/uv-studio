"""Browser Product Truth proof for named-model generation into shared Shot/Take/Timeline."""

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
    _start_process,
    _wait_http,
)


class NamedGenerationBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("Named-generation browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-named-generation-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update(
            {
                "PYTHONUNBUFFERED": "1",
                "NEXT_TELEMETRY_DISABLED": "1",
                "UV_STUDIO_PROJECTS_DIR": str(cls.temp_root / "projects"),
                "UV_STUDIO_CONFIG_DIR": str(cls.temp_root / "config"),
                "UV_STUDIO_E2E_TEST_GENERATION": "1",
            }
        )
        cls.backend = _start_process(
            [sys.executable, "-m", "uv_studio.server"],
            cwd=ROOT,
            env=env,
            log_path=cls.artifact_dir / "named-generation-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "named-generation-frontend.log",
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
            viewport={"width": 1600, "height": 1500},
            locale="ru-RU",
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(60_000)
        return page

    def test_visible_named_model_generates_take_accepts_to_timeline_and_undo_keeps_job(self) -> None:
        page = self._new_page()
        title = "Named generation E2E"
        scene_title = "Контрольная сцена"
        shot_intent = "Герой смотрит прямо в камеру"
        generated_label = "Generated · UV Image · E2E test only"

        try:
            page.goto("/projects")
            direction = page.get_by_role("button").filter(has_text="Микродрама / сюжетное видео")
            expect(direction).to_be_visible()
            direction.click()
            page.get_by_placeholder("Название проекта").fill(title)
            page.get_by_role("button", name="Создать и открыть Studio", exact=True).click()
            page.wait_for_url("**/projects/*/studio")
            expect(page.get_by_role("heading", name="Сцены, кадры и дубли", exact=True)).to_be_visible()
            expect(page.get_by_text("Named model → Job → новый дубль", exact=True)).to_be_visible()

            path_parts = urllib.parse.urlparse(page.url).path.strip("/").split("/")
            project_id = urllib.parse.unquote(path_parts[1])

            page.get_by_label("Название production-сцены", exact=True).fill(scene_title)
            page.get_by_role("button", name="Создать сцену", exact=True).click()
            expect(page.locator("p").filter(has_text=scene_title).first).to_be_visible()

            page.get_by_label("Сцена для кадра", exact=True).select_option(label=scene_title)
            page.get_by_label("Замысел production-кадра", exact=True).fill(shot_intent)
            page.get_by_role("button", name="Создать кадр", exact=True).click()
            expect(page.locator("p").filter(has_text=shot_intent).first).to_be_visible()

            generation_shot = page.get_by_label("Кадр для генерации", exact=True)
            expect(generation_shot).to_be_visible()
            generation_shot.select_option(label=shot_intent)
            model = page.get_by_label("Модель генерации", exact=True)
            model.select_option(label="UV Image · E2E test only")
            expect(page.get_by_text("local · free", exact=True)).to_be_visible()
            page.get_by_label("Запрос для генерации", exact=True).fill(
                "Портрет героя в холодном вечернем свете"
            )
            page.get_by_text("Generation Contract", exact=True).click()
            page.get_by_label("Фиксированные ограничения генерации", exact=True).fill(
                "тот же герой\nкрасный шарф"
            )
            page.get_by_label("Запрещённые изменения генерации", exact=True).fill(
                "не менять личность"
            )

            page.get_by_role("button", name="Сгенерировать дубль", exact=True).click()
            expect(page.get_by_text("Готово", exact=True)).to_be_visible(timeout=60_000)
            expect(page.get_by_text("Новый Take:", exact=False)).to_be_visible(timeout=60_000)

            accept = page.get_by_role(
                "button",
                name=f"Принять дубль {generated_label}",
                exact=True,
            )
            expect(accept).to_be_visible(timeout=60_000)

            jobs = _api_json(
                "GET",
                _project_path(project_id, "/studio/generation/jobs"),
            )
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["status"], "succeeded")
            self.assertEqual(jobs[0]["request"]["model_id"], "uv.image.e2e_test")
            self.assertEqual(
                jobs[0]["request"]["generation_contract"]["fixed_constraints"],
                ["тот же герой", "красный шарф"],
            )
            job_id = jobs[0]["job_id"]
            generated_take_id = jobs[0]["attempts"][0]["take_id"]
            generated_reference_id = jobs[0]["attempts"][0]["output_reference_id"]

            project = _api_json("GET", f"/api/uv/projects/{project_id}")
            artifact = next(
                item for item in project["artifacts"] if item["id"] == generated_reference_id
            )
            self.assertEqual(artifact["metadata"]["generation"]["job_id"], job_id)
            self.assertEqual(artifact["metadata"]["generation"]["model_id"], "uv.image.e2e_test")
            self.assertTrue(artifact["metadata"]["executor"]["test_only"])

            accept.click()
            expect(page.get_by_text("Принят", exact=True)).to_be_visible(timeout=60_000)
            accepted = _api_json("GET", _project_path(project_id, "/studio/production"))
            self.assertEqual(accepted["shots"][0]["accepted_take_id"], generated_take_id)
            timeline = _api_json("GET", _project_path(project_id, "/studio/timeline"))
            self.assertEqual(
                timeline["tracks"][0]["clips"][0]["reference_id"],
                generated_reference_id,
            )

            page.get_by_role("button", name="Отменить последнее действие проекта", exact=True).click()
            expect(page.get_by_text("Принят", exact=True)).to_have_count(0, timeout=60_000)
            undone = _api_json("GET", _project_path(project_id, "/studio/production"))
            self.assertIsNone(undone["shots"][0]["accepted_take_id"])
            self.assertIn(generated_take_id, undone["shots"][0]["take_ids"])

            durable_jobs = _api_json(
                "GET",
                _project_path(project_id, "/studio/generation/jobs"),
            )
            self.assertEqual(len(durable_jobs), 1)
            self.assertEqual(durable_jobs[0]["job_id"], job_id)
            self.assertEqual(durable_jobs[0]["status"], "succeeded")
            self.assertEqual(len(durable_jobs[0]["attempts"]), 1)
            expect(page.get_by_text("Готово", exact=True)).to_be_visible()

            page.screenshot(
                path=str(self.artifact_dir / "named-generation-outcome.png"),
                full_page=True,
            )
        except Exception:
            page.screenshot(
                path=str(self.artifact_dir / "named-generation-outcome-failure.png"),
                full_page=True,
            )
            raise


if __name__ == "__main__":
    unittest.main()
