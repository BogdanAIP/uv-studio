"""Browser regressions for Stage 8 composition workspaces and Product Orchestrator routing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from legacy_project_fixture import seed_legacy_project
from test_user_outcomes import (
    BACKEND_ORIGIN,
    FRONTEND,
    FRONTEND_ORIGIN,
    ROOT,
    _start_process,
    _wait_http,
)


def _run(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}"
        )


def _video_fixture(path: Path) -> None:
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=green:s=320x180:r=24:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ]
    )


def _image_fixture(path: Path) -> None:
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=orange:s=320x180:d=0.04",
            "-frames:v", "1", "-update", "1", str(path),
        ]
    )


def _audio_fixture(path: Path) -> None:
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=3",
            "-c:a", "pcm_s16le", str(path),
        ]
    )


def _api_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BACKEND_ORIGIN}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urllib.request.urlopen(request, timeout=60.0) as response:
        return json.loads(response.read().decode("utf-8"))


class Stage8CompositionBrowserOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise unittest.SkipTest("Stage 8 composition browser E2E requires FFmpeg/FFprobe")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("Stage 8 composition browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-studio-stage8-composition-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)
        cls.video = cls.temp_root / "story-scene.mp4"
        cls.image = cls.temp_root / "product.png"
        cls.audio = cls.temp_root / "narration.wav"
        _video_fixture(cls.video)
        _image_fixture(cls.image)
        _audio_fixture(cls.audio)

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
            log_path=cls.artifact_dir / "stage8-composition-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "stage8-composition-frontend.log",
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

    def _create_project(self, title: str, recipe_id: str) -> tuple[str, str]:
        project_id = seed_legacy_project(
            self.temp_root / "projects",
            title=title,
            recipe_id=recipe_id,
        )
        return project_id, urllib.parse.quote(project_id, safe="")

    def _assert_workspace(self, encoded_id: str, recipe_id: str, kind: str, role: str) -> None:
        payload = _api_json("GET", f"/api/uv/projects/{encoded_id}/stage8/workspace")
        workspace = payload["workspace"]
        self.assertEqual(workspace["recipe_id"], recipe_id)
        self.assertEqual(len(workspace["revision_sha256"]), 64)
        self.assertEqual(len(workspace["sources"]), 1)
        self.assertEqual(workspace["sources"][0]["kind"], kind)
        self.assertEqual(workspace["sources"][0]["role"], role)
        self.assertEqual(len(workspace["sources"][0]["sha256"]), 64)

    def test_story_commercial_narrated_round_trip_and_free_routes_to_targeted_edit(self) -> None:
        page = self._new_page()

        _story_id, story_encoded = self._create_project("E2E Stage 8 Story", "story_video")
        page.goto(f"/projects/{story_encoded}")
        expect(page.get_by_role("heading", name="Сюжетное рабочее пространство", exact=True)).to_be_visible()
        page.get_by_label("Stage 8 brief").fill("Герой возвращается домой после долгого путешествия")
        page.get_by_label("Stage 8 script").fill("Сцена 1. Герой входит в кадр.")
        page.locator('input[aria-label="Stage 8 workspace video"]').set_input_files(str(self.video))
        expect(page.get_by_label(f"Использовать {self.video.name}")).to_be_checked(timeout=60_000)
        page.get_by_role("button", name="Сохранить рабочее пространство", exact=True).click()
        expect(page.get_by_text("Рабочее пространство сохранено с точной SHA-привязкой выбранных материалов.", exact=True)).to_be_visible(timeout=60_000)
        self._assert_workspace(story_encoded, "story_video", "video", "story_video")
        page.reload()
        expect(page.get_by_label("Stage 8 brief")).to_have_value("Герой возвращается домой после долгого путешествия")
        expect(page.get_by_label(f"Использовать {self.video.name}")).to_be_checked(timeout=60_000)

        _commercial_id, commercial_encoded = self._create_project(
            "E2E Stage 8 Commercial", "commercial_product"
        )
        page.goto(f"/projects/{commercial_encoded}")
        expect(page.get_by_role("heading", name="Продуктовое рабочее пространство", exact=True)).to_be_visible()
        page.get_by_label("Stage 8 brief").fill("Показать продукт крупно и сохранить точные детали упаковки")
        page.get_by_label("Stage 8 script").fill("Текст оффера без подмены продукта")
        page.locator('input[aria-label="Stage 8 workspace image"]').set_input_files(str(self.image))
        expect(page.get_by_label(f"Использовать {self.image.name}")).to_be_checked(timeout=60_000)
        page.get_by_role("button", name="Сохранить рабочее пространство", exact=True).click()
        expect(page.get_by_text("Рабочее пространство сохранено с точной SHA-привязкой выбранных материалов.", exact=True)).to_be_visible(timeout=60_000)
        self._assert_workspace(commercial_encoded, "commercial_product", "image", "product_image")
        page.reload()
        expect(page.get_by_label("Stage 8 script")).to_have_value("Текст оффера без подмены продукта")
        expect(page.get_by_label(f"Использовать {self.image.name}")).to_be_checked(timeout=60_000)

        _narrated_id, narrated_encoded = self._create_project("E2E Narrated", "narrated_video")
        page.goto(f"/projects/{narrated_encoded}")
        expect(page.get_by_role("heading", name="Видео с дикторской дорожкой", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Подготовленная речь", exact=True)).to_be_visible()
        expect(page.locator('input[aria-label="Stage 8 workspace audio"]')).to_have_count(0)
        page.get_by_label("Stage 8 brief").fill("Коротко объяснить процесс")
        page.get_by_label("Stage 8 script").fill("Три секунды проверенного текста диктора.")
        page.locator('input[aria-label="Stage 8 workspace image"]').set_input_files(str(self.image))
        expect(page.get_by_label(f"Использовать {self.image.name}")).to_be_checked(timeout=60_000)
        page.get_by_role("button", name="Сохранить рабочее пространство", exact=True).click()
        expect(page.get_by_text("Рабочее пространство сохранено с точной SHA-привязкой выбранных материалов.", exact=True)).to_be_visible(timeout=60_000)
        self._assert_workspace(narrated_encoded, "narrated_video", "image", "narrated_image")

        page.locator('input[aria-label="Narrated prepared audio upload"]').set_input_files(str(self.audio))
        expect(page.get_by_text("Дикторская дорожка импортирована как проверяемый PreparedAudio проекта.", exact=True)).to_be_visible(timeout=60_000)
        render_button = page.get_by_role("button", name="Собрать видео с дикторской дорожкой", exact=True)
        expect(render_button).to_be_enabled(timeout=60_000)
        render_button.click()
        expect(page.get_by_text("Новый Narrated мастер собран и зарегистрирован в проекте.", exact=True)).to_be_visible(timeout=60_000)
        narrated_workflow = _api_json("GET", f"/api/uv/projects/{narrated_encoded}/workflow")
        self.assertEqual(narrated_workflow["readiness"], "ready")
        self.assertIsNotNone(narrated_workflow["current_outcome"])
        self.assertEqual(narrated_workflow["current_outcome"]["lifecycle"], "narrated_video_render")

        _free_id, free_encoded = self._create_project("E2E Targeted Edit Routing", "free_project")
        page.goto(f"/projects/{free_encoded}")
        expect(
            page.get_by_role("heading", name="Точечное редактирование исходного видео", exact=True)
        ).to_be_visible()
        expect(page.get_by_role("heading", name="Свободное рабочее пространство", exact=True)).to_have_count(0)
        expect(page.get_by_text("Дубляж в том же проекте и таймлайне", exact=True)).to_have_count(0)
        expect(page.get_by_text("Непрерывность связанных кадров", exact=True)).to_have_count(0)
        expect(page.locator('input[aria-label="Stage 8 workspace audio"]')).to_have_count(0)
        expect(page.get_by_role("heading", name="Нужна подготовка", exact=True)).to_be_visible()

        page.screenshot(path=str(self.artifact_dir / "stage8-composition-workspaces.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()
