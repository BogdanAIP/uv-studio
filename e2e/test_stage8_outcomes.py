"""Real browser outcomes for Stage 8 local media modes and optional lip-sync gating."""

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

from test_user_outcomes import (
    BACKEND_ORIGIN,
    FRONTEND,
    FRONTEND_ORIGIN,
    ROOT,
    _select_option_containing,
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


def _image_fixture(path: Path, *, color: str) -> None:
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
            f"color=c={color}:s=320x180:d=0.04",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(path),
        ]
    )


def _audio_fixture(path: Path, *, frequency: int = 660, duration_sec: int = 4) -> None:
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
            f"sine=frequency={frequency}:sample_rate=48000:duration={duration_sec}",
            "-c:a",
            "pcm_s16le",
            str(path),
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


class Stage8BrowserOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise unittest.SkipTest("Stage 8 browser E2E requires FFmpeg/FFprobe")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("Stage 8 browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-studio-stage8-browser-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)

        cls.red_image = cls.temp_root / "red.png"
        cls.blue_image = cls.temp_root / "blue.png"
        cls.audio = cls.temp_root / "master.wav"
        _image_fixture(cls.red_image, color="red")
        _image_fixture(cls.blue_image, color="blue")
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
        env.pop("UV_STUDIO_MUSETALK_ROOT", None)
        env.pop("UV_STUDIO_MUSETALK_PYTHON", None)

        cls.backend = _start_process(
            [sys.executable, "-m", "uv_studio.server"],
            cwd=ROOT,
            env=env,
            log_path=cls.artifact_dir / "stage8-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "stage8-frontend.log",
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
        created = _api_json(
            "POST",
            "/api/uv/projects",
            {"title": title, "recipe_id": recipe_id},
        )
        project_id = created["project_id"]
        return project_id, urllib.parse.quote(project_id, safe="")

    def test_photo_visualizer_and_optional_lipsync_user_paths(self) -> None:
        page = self._new_page()

        photo_id, photo_encoded = self._create_project("E2E Stage 8 Photo", "photo_to_video")
        page.goto(f"/projects/{photo_encoded}")
        expect(page.get_by_role("heading", name="Фотографии → видео", exact=True)).to_be_visible()
        page.locator('input[aria-label="Изображения Stage 8"]').set_input_files(
            [str(self.red_image), str(self.blue_image)]
        )
        expect(page.get_by_text("1. red.png", exact=True)).to_be_visible(timeout=60_000)
        expect(page.get_by_text("2. blue.png", exact=True)).to_be_visible(timeout=60_000)
        page.locator('input[aria-label="Аудио Stage 8"]').set_input_files(str(self.audio))
        photo_audio = page.get_by_label("Аудио для фото-видео")
        expect(photo_audio).to_be_visible(timeout=60_000)
        _select_option_containing(photo_audio, self.audio.name)
        page.get_by_role("button", name="Собрать видео из фотографий", exact=True).click()
        expect(page.get_by_role("link", name="Открыть готовый рендер", exact=True)).to_be_visible(
            timeout=120_000
        )

        photo_project = _api_json("GET", f"/api/uv/projects/{photo_encoded}")
        photo_artifacts = [
            item
            for item in photo_project["artifacts"]
            if item.get("metadata", {}).get("lifecycle") == "photo_to_video_render"
        ]
        self.assertEqual(len(photo_artifacts), 1)
        self.assertEqual(
            [item["source_id"] for item in photo_artifacts[0]["metadata"]["image_bindings"]],
            [
                item["id"]
                for item in photo_project["sources"]
                if item["kind"] == "image"
            ],
        )
        self.assertIsNotNone(photo_artifacts[0]["metadata"]["audio_binding"])

        visualizer_id, visualizer_encoded = self._create_project(
            "E2E Stage 8 Visualizer", "visualizer"
        )
        page.goto(f"/projects/{visualizer_encoded}")
        expect(page.get_by_role("heading", name="Аудио → визуализатор", exact=True)).to_be_visible()
        page.locator('input[aria-label="Аудио Stage 8"]').set_input_files(str(self.audio))
        visualizer_audio = page.get_by_label("Master-аудио визуализатора")
        expect(visualizer_audio).to_be_visible(timeout=60_000)
        _select_option_containing(visualizer_audio, self.audio.name)
        page.locator('input[aria-label="Изображения Stage 8"]').set_input_files(str(self.blue_image))
        artwork = page.get_by_label("Обложка визуализатора")
        expect(artwork).to_be_visible(timeout=60_000)
        _select_option_containing(artwork, self.blue_image.name)
        page.get_by_role("button", name="Собрать аудиовизуализатор", exact=True).click()
        expect(page.get_by_role("link", name="Открыть готовый рендер", exact=True)).to_be_visible(
            timeout=120_000
        )

        visualizer_project = _api_json("GET", f"/api/uv/projects/{visualizer_encoded}")
        visualizer_artifacts = [
            item
            for item in visualizer_project["artifacts"]
            if item.get("metadata", {}).get("lifecycle") == "audio_visualizer_render"
        ]
        self.assertEqual(len(visualizer_artifacts), 1)
        self.assertIsNotNone(visualizer_artifacts[0]["metadata"]["artwork_binding"])
        self.assertEqual(
            visualizer_artifacts[0]["metadata"]["audio_binding"]["source_id"],
            next(item["id"] for item in visualizer_project["sources"] if item["kind"] == "audio"),
        )

        performance_id, performance_encoded = self._create_project(
            "E2E Stage 8 Performance", "performance_lip_sync"
        )
        page.goto(f"/projects/{performance_encoded}")
        expect(
            page.get_by_role("heading", name="Портрет + готовая речь → lip-sync", exact=True)
        ).to_be_visible()
        expect(page.get_by_text("configuration_required", exact=True)).to_be_visible(timeout=60_000)
        page.locator('input[aria-label="Портрет lip-sync"]').set_input_files(str(self.red_image))
        performance_portrait = page.get_by_label("Выбранный портрет lip-sync")
        _select_option_containing(performance_portrait, self.red_image.name)
        page.locator('input[aria-label="Готовая речь lip-sync"]').set_input_files(str(self.audio))
        performance_speech = page.get_by_label("Выбранная речь lip-sync")
        _select_option_containing(performance_speech, self.audio.name)
        expect(page.get_by_text("configuration_required", exact=True)).to_be_visible(timeout=60_000)
        expect(page.get_by_role("button", name="Выполнить lip-sync", exact=True)).to_be_disabled()

        performance_project = _api_json("GET", f"/api/uv/projects/{performance_encoded}")
        self.assertEqual(
            sorted(item["kind"] for item in performance_project["sources"]),
            ["audio", "image"],
        )
        self.assertEqual(
            [
                item
                for item in performance_project["artifacts"]
                if item.get("metadata", {}).get("lifecycle") == "performance_lip_sync_render"
            ],
            [],
        )

        page.screenshot(path=str(self.artifact_dir / "stage8-additional-recipes-final.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()
