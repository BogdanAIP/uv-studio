"""Browser proof for the shared Scene -> Shot -> Take micro-drama production path."""

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


def _video_fixture(path: Path) -> None:
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=640x360:r=30:d=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ]
    )


class MicroDramaProductionBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None:
            raise unittest.SkipTest("Micro-drama browser E2E requires FFmpeg")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("Micro-drama browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-micro-drama-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)
        cls.video = cls.temp_root / "platform-take.mp4"
        _video_fixture(cls.video)

        env = os.environ.copy()
        env.update(
            {
                "PYTHONUNBUFFERED": "1",
                "NEXT_TELEMETRY_DISABLED": "1",
                "UV_STUDIO_PROJECTS_DIR": str(cls.temp_root / "projects"),
                "UV_STUDIO_CONFIG_DIR": str(cls.temp_root / "config"),
            }
        )
        cls.backend = _start_process(
            [sys.executable, "-m", "uv_studio.server"],
            cwd=ROOT,
            env=env,
            log_path=cls.artifact_dir / "micro-drama-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "micro-drama-frontend.log",
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
            viewport={"width": 1600, "height": 1400},
            locale="ru-RU",
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(60_000)
        return page

    def test_micro_drama_scene_shot_take_accept_undo_redo_from_visible_studio(self) -> None:
        page = self._new_page()
        title = "Micro-drama E2E"
        scene_title = "Встреча на платформе"
        shot_intent = "Крупный план героя перед отправлением"

        try:
            page.goto("/projects")
            direction = page.get_by_role("button").filter(has_text="Микродрама / сюжетное видео")
            expect(direction).to_be_visible()
            direction.click()
            page.get_by_placeholder("Название проекта").fill(title)
            page.get_by_role("button", name="Создать и открыть Studio", exact=True).click()
            page.wait_for_url("**/projects/*/studio")
            expect(page.get_by_role("heading", name="Сцены, кадры и дубли", exact=True)).to_be_visible()

            path_parts = urllib.parse.urlparse(page.url).path.strip("/").split("/")
            self.assertEqual(path_parts[0], "projects")
            self.assertEqual(path_parts[-1], "studio")
            project_id = urllib.parse.unquote(path_parts[1])

            page.get_by_label("Импортировать медиа в Studio", exact=True).set_input_files(str(self.video))
            expect(page.get_by_text(self.video.name, exact=True).first).to_be_visible(timeout=60_000)
            production_media = page.get_by_label("Медиа для production-дубля", exact=True)
            expect(production_media).to_be_visible()
            production_media.select_option(label=self.video.name)

            page.get_by_label("Название production-сцены", exact=True).fill(scene_title)
            page.get_by_label("Краткое описание production-сцены", exact=True).fill(
                "Герой принимает решение у уходящего поезда"
            )
            page.get_by_role("button", name="Создать сцену", exact=True).click()
            expect(page.get_by_text(scene_title, exact=True).first).to_be_visible()

            page.get_by_label("Сцена для кадра", exact=True).select_option(label=scene_title)
            page.get_by_label("Замысел production-кадра", exact=True).fill(shot_intent)
            page.get_by_role("button", name="Создать кадр", exact=True).click()
            expect(page.get_by_text(shot_intent, exact=True).first).to_be_visible()

            page.get_by_label("Кадр для дубля", exact=True).select_option(label=shot_intent)
            page.get_by_role(
                "button", name="Добавить выбранное медиа как дубль", exact=True
            ).click()
            accept = page.get_by_role("button", name=f"Принять дубль {self.video.name}", exact=True)
            expect(accept).to_be_visible()

            page.get_by_label("Название истории", exact=True).fill("Последний поезд")
            page.get_by_label("Завязка истории", exact=True).fill("Герой должен решить, уезжать ли навсегда")
            page.get_by_label("Синопсис истории", exact=True).fill("Короткая история выбора и расставания")
            page.get_by_label("Имя персонажа", exact=True).fill("Алекс")
            page.get_by_label("Описание персонажа", exact=True).fill("Пассажир с красным шарфом")
            page.get_by_role("button", name="Добавить персонажа", exact=True).click()
            page.get_by_label("Название локации", exact=True).fill("Платформа")
            page.get_by_label("Описание локации", exact=True).fill("Ночная станция, холодный синий свет")
            page.get_by_role("button", name="Добавить локацию", exact=True).click()
            page.get_by_label("Сцена для непрерывности", exact=True).select_option(label=scene_title)
            page.get_by_label("Локация сцены", exact=True).select_option(label="Платформа")
            page.get_by_role("button", name="Персонаж continuity Алекс", exact=True).click()
            page.get_by_label("Канонические факты сцены", exact=True).fill("Алекс носит красный шарф")
            page.get_by_label("Заметки по непрерывности сцены", exact=True).fill("Сохранять холодный синий свет")
            with page.expect_response(
                lambda response: (
                    "/studio/production/commands" in response.url
                    and response.request.method == "POST"
                )
            ) as saved_context:
                page.get_by_role("button", name="Сохранить историю и непрерывность", exact=True).click()
            self.assertEqual(saved_context.value.status, 201)

            micro = _api_json("GET", _project_path(project_id, "/studio/production/micro-drama"))
            self.assertEqual(micro["story"]["title"], "Последний поезд")
            self.assertEqual(micro["characters"][0]["name"], "Алекс")
            self.assertEqual(micro["locations"][0]["name"], "Платформа")
            self.assertEqual(micro["scene_continuity"][0]["canon_facts"], ["Алекс носит красный шарф"])

            accept = page.get_by_role("button", name=f"Принять дубль {self.video.name}", exact=True)
            expect(accept).to_be_visible()
            accept.click()
            expect(page.get_by_text("Принят", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name=f"Клип {self.video.name}", exact=True)).to_be_visible(
                timeout=60_000
            )

            accepted = _api_json("GET", _project_path(project_id, "/studio/production"))
            self.assertIsNotNone(accepted["shots"][0]["accepted_take_id"])
            self.assertEqual(len(accepted["shots"][0]["timeline_clip_ids"]), 1)
            timeline = _api_json("GET", _project_path(project_id, "/studio/timeline"))
            self.assertEqual(timeline["tracks"][0]["clips"][0]["reference_id"], accepted["takes"][0]["reference_id"])

            page.get_by_role("button", name="Отменить последнее действие проекта", exact=True).click()
            expect(page.get_by_text("Принят", exact=True)).to_have_count(0, timeout=60_000)
            expect(page.get_by_role("button", name=f"Клип {self.video.name}", exact=True)).to_have_count(0)
            undone = _api_json("GET", _project_path(project_id, "/studio/production"))
            self.assertIsNone(undone["shots"][0]["accepted_take_id"])

            page.get_by_role("button", name="Повторить отменённое действие проекта", exact=True).click()
            expect(page.get_by_text("Принят", exact=True)).to_be_visible(timeout=60_000)
            expect(page.get_by_role("button", name=f"Клип {self.video.name}", exact=True)).to_be_visible()
            redone = _api_json("GET", _project_path(project_id, "/studio/production"))
            self.assertIsNotNone(redone["shots"][0]["accepted_take_id"])

            page.screenshot(path=str(self.artifact_dir / "micro-drama-production-outcome.png"), full_page=True)
        except Exception:
            page.screenshot(
                path=str(self.artifact_dir / "micro-drama-production-outcome-failure.png"),
                full_page=True,
            )
            raise


if __name__ == "__main__":
    unittest.main()
