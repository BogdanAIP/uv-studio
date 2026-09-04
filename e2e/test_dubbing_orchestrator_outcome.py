"""Browser evidence for the dedicated Product Orchestrator Dubbing workspace.

This is Class B informed regression evidence, not Class C cold-start acceptance: the
Dubbing legacy identity is seeded directly as compatibility state, while optional
whisper.cpp remains outside CI prerequisites. From the empty project onward the
canonical Dubbing journey is driven through visible production UI controls: source
import, manual verified transcript, translation, prepared speech, Review, Accept and
final render.
"""

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
    _card_for,
    _ffmpeg_fixture,
    _project_path,
    _speech_fixture,
    _start_process,
    _wait_http,
)


class DubbingOrchestratorBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise unittest.SkipTest("dedicated Dubbing browser E2E requires FFmpeg/FFprobe")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("dedicated Dubbing browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-dubbing-orchestrator-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)

        cls.source_video = cls.temp_root / "dubbing-source-e2e.mp4"
        cls.prepared_speech = cls.temp_root / "dubbing-speech-e2e.wav"
        _ffmpeg_fixture(cls.source_video, duration=5.0, color="purple", tone_hz=210)
        _speech_fixture(cls.prepared_speech)

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
            log_path=cls.artifact_dir / "dubbing-orchestrator-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "dubbing-orchestrator-frontend.log",
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
        page.set_default_timeout(30_000)
        return page

    def test_dedicated_dubbing_workspace_starts_and_reaches_rendered_outcome(self) -> None:
        page = self._new_page()
        title = "Dedicated Dubbing E2E"
        project_id = seed_legacy_project(
            self.temp_root / "projects",
            title=title,
            recipe_id="dubbing",
        )
        encoded = urllib.parse.quote(project_id, safe="")
        page.goto(f"/projects/{encoded}")

        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Исходное видео для дубляжа", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Дубляж в том же проекте и таймлайне", exact=True)).to_be_visible()
        self.assertEqual(
            page.get_by_role("heading", name="Точечное редактирование исходного видео", exact=True).count(),
            0,
            "dedicated Dubbing workspace must not mount generic ProjectEditor",
        )
        self.assertEqual(
            page.get_by_text("Непрерывность связанных кадров", exact=True).count(),
            0,
            "dedicated Dubbing workspace must not leak Sequence Continuity",
        )

        source_input = page.locator('input[aria-label="Импортировать видео для дубляжа"]')
        expect(source_input).to_have_count(1)
        source_input.set_input_files(str(self.source_video))
        expect(page.get_by_text(f"Видео «{self.source_video.name}» добавлено в Project Store.", exact=True)).to_be_visible(
            timeout=45_000
        )
        expect(
            page.get_by_label("Видео для ручного transcript", exact=True).locator("option:checked")
        ).to_have_text(self.source_video.name, timeout=45_000)

        expect(page.get_by_role("heading", name="Проверенный transcript без ASR", exact=True)).to_be_visible()
        page.get_by_label("Начало ручного transcript", exact=True).fill("1")
        page.get_by_label("Конец ручного transcript", exact=True).fill("2")
        page.get_by_label("Текст ручного transcript", exact=True).fill("hello world")
        page.get_by_role("button", name="Сохранить проверенный transcript", exact=True).click()
        expect(
            page.get_by_text("Проверенный transcript сохранён в каноническое состояние проекта.", exact=True)
        ).to_be_visible(timeout=30_000)

        dubbing = page.get_by_text(
            "Дубляж в том же проекте и таймлайне", exact=True
        ).locator("xpath=ancestor::section[1]")
        translation_card = _card_for(dubbing, "Transcript и перевод")
        expect(translation_card.get_by_role("paragraph").filter(has_text="hello world")).to_be_visible(
            timeout=30_000
        )
        translation_card.locator("textarea").first.fill("привет мир")
        translation_card.get_by_role("button", name="Сохранить перевод", exact=True).click()
        expect(dubbing.get_by_text("Перевод сохранён и привязан", exact=False)).to_be_visible(timeout=30_000)

        audio_card = _card_for(dubbing, "Подготовленная речь")
        audio_picker = audio_card.locator('input[type="file"][accept="audio/*"]')
        audio_picker.set_input_files(str(self.prepared_speech))
        expect(audio_card.locator("select").first.locator("option:checked")).to_have_text(
            self.prepared_speech.name,
            timeout=30_000,
        )
        audio_card.get_by_role("button", name="Привязать к тексту и диапазону", exact=True).click()
        expect(dubbing.get_by_text("Голосовая дорожка привязана", exact=False)).to_be_visible(timeout=30_000)

        review_card = _card_for(dubbing, "Review → Accept")
        review_card.get_by_label(
            "Содержание и произношение проверены по выбранному тексту", exact=True
        ).check()
        review_card.get_by_label(
            "Синхронизация с видео проверена человеком", exact=True
        ).check()
        review_card.get_by_role("button", name="Review: approved", exact=True).click()
        expect(review_card.get_by_text("approved", exact=True)).to_be_visible(timeout=45_000)
        expect(review_card.get_by_text("timing: pass", exact=True)).to_be_visible()
        expect(review_card.get_by_text("audio: pass", exact=True)).to_be_visible()

        review_card.get_by_role("button", name="Принять в timeline", exact=True).click()
        expect(dubbing.get_by_text("Одобренная озвучка принята", exact=False)).to_be_visible(timeout=30_000)

        render_card = dubbing.get_by_text(
            "Материализовать видео + принятый дубляж", exact=True
        ).locator("xpath=ancestor::div[contains(@class,'rounded-2xl')][1]")
        render_card.get_by_role("button", name="Собрать мастер", exact=True).click()
        expect(render_card.get_by_text("Мастер с принятой озвучкой", exact=True)).to_be_visible(
            timeout=90_000
        )

        workflow = _api_json("GET", _project_path(project_id, "/workflow"))
        self.assertEqual(workflow["recipe_id"], "dubbing")
        self.assertEqual([item["workspace_id"] for item in workflow["relevant_workspaces"]], ["dubbing"])
        self.assertIsNotNone(workflow["current_outcome"])
        self.assertEqual(workflow["current_outcome"]["metadata"]["lifecycle"], "dubbing_render")
        page.screenshot(
            path=str(self.artifact_dir / "dedicated-dubbing-outcome.png"),
            full_page=True,
        )


if __name__ == "__main__":
    unittest.main()
