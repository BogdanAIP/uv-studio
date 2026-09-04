"""Real browser outcome for the complete provider-free Stage 7 Music Video path."""

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


def _video_fixture(path: Path, *, color: str, tone_hz: int) -> None:
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
            f"color=c={color}:s=320x180:r=24:d=11",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={tone_hz}:sample_rate=48000:duration=11",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ]
    )


def _song_fixture(path: Path) -> None:
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
            "sine=frequency=880:sample_rate=48000:duration=21",
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


class MusicVideoBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise unittest.SkipTest("real Music Video browser E2E requires FFmpeg/FFprobe")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("real Music Video browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-studio-music-browser-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)
        cls.song = cls.temp_root / "master-song.wav"
        cls.red_video = cls.temp_root / "red-visual.mp4"
        cls.blue_video = cls.temp_root / "blue-visual.mp4"
        _song_fixture(cls.song)
        _video_fixture(cls.red_video, color="red", tone_hz=440)
        _video_fixture(cls.blue_video, color="blue", tone_hz=660)

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
            log_path=cls.artifact_dir / "music-video-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "music-video-frontend.log",
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
        page.set_default_timeout(45_000)
        return page

    def test_song_to_music_map_to_assembly_to_master_render(self) -> None:
        project_id = seed_legacy_project(
            self.temp_root / "projects",
            title="E2E Stage 7 Music Video",
            recipe_id="music_video",
        )
        encoded_id = urllib.parse.quote(project_id, safe="")

        page = self._new_page()
        mutation_posts: list[str] = []

        def capture_mutation_request(request: Any) -> None:
            if request.method == "POST" and f"/api/uv/projects/{encoded_id}/" in request.url:
                mutation_posts.append(request.url)

        page.on("request", capture_mutation_request)
        page.goto(f"/projects/{encoded_id}")
        expect(page.get_by_role("heading", name="E2E Stage 7 Music Video", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Песня → Music Map → музыкальная режиссура → проверка ритма", exact=True)).to_be_visible()

        page.locator('input[aria-label="Файл песни"]').set_input_files(str(self.song))
        expect(page.get_by_role("combobox", name="Песня Music Video Mode")).to_be_visible(timeout=60_000)
        page.get_by_label("Начало музыкального фрагмента").fill("0")
        page.get_by_label("Конец музыкального фрагмента").fill("20")
        page.get_by_role("button", name="+ Добавить секцию", exact=True).click()
        page.get_by_label("Начало музыкальной секции 1").fill("0")
        page.get_by_label("Конец музыкальной секции 1").fill("20")
        page.get_by_role("button", name="+ Добавить маркер", exact=True).click()
        page.get_by_label("Тип музыкального маркера 1").select_option("cut_point")
        page.get_by_label("Время музыкального маркера 1").fill("10")
        page.get_by_role("button", name="Сохранить Music Map", exact=True).click()
        expect(page.get_by_text("Music Map сохранён и привязан к точным байтам песни.", exact=True)).to_be_visible(timeout=60_000)

        page.get_by_role("button", name="Черновик по Music Map", exact=True).click()
        expect(page.get_by_label("Замысел музыкального кадра 1")).to_be_visible()
        expect(page.get_by_label("Замысел музыкального кадра 2")).to_be_visible()
        page.get_by_role("button", name="Сохранить режиссёрский план", exact=True).click()
        expect(page.get_by_text("Music Director сохранён для точной ревизии Music Map.", exact=True)).to_be_visible(timeout=60_000)

        assembly_heading = page.get_by_role(
            "heading", name="Визуальные материалы → Assembly Plan → master-render", exact=True
        )
        expect(assembly_heading).to_be_visible(timeout=60_000)
        assembly = assembly_heading.locator("xpath=ancestor::section[1]")

        assembly.locator('input[aria-label="Видео для Music Assembly"]').set_input_files(str(self.red_video))
        expect(assembly.get_by_text("Доступно источников: 1", exact=True)).to_be_visible(timeout=60_000)
        expect(
            assembly.get_by_role("button", name="Загрузить видео", exact=True)
        ).to_be_enabled(timeout=60_000)
        assembly = page.get_by_role(
            "heading", name="Визуальные материалы → Assembly Plan → master-render", exact=True
        ).locator("xpath=ancestor::section[1]")
        assembly.locator('input[aria-label="Видео для Music Assembly"]').set_input_files(str(self.blue_video))
        expect(assembly.get_by_text("Доступно источников: 2", exact=True)).to_be_visible(timeout=60_000)
        expect(
            assembly.get_by_role("button", name="Загрузить видео", exact=True)
        ).to_be_enabled(timeout=60_000)
        assembly = page.get_by_role(
            "heading", name="Визуальные материалы → Assembly Plan → master-render", exact=True
        ).locator("xpath=ancestor::section[1]")

        first_source = assembly.get_by_label("Видеоисточник музыкального кадра 1")
        second_source = assembly.get_by_label("Видеоисточник музыкального кадра 2")
        _select_option_containing(first_source, self.red_video.name)
        _select_option_containing(second_source, self.blue_video.name)
        assembly.get_by_role("button", name="Сохранить Assembly Plan", exact=True).click()

        assembly = page.get_by_role(
            "heading", name="Визуальные материалы → Assembly Plan → master-render", exact=True
        ).locator("xpath=ancestor::section[1]")
        render_button = assembly.get_by_role("button", name="Собрать клип", exact=True)
        expect(render_button).to_be_enabled(timeout=60_000)
        render_button.click()
        rendered_link = assembly.get_by_role("link", name="Открыть готовый рендер", exact=True)
        expect(rendered_link).to_be_visible(timeout=120_000)

        project = _api_json("GET", f"/api/uv/projects/{encoded_id}")
        rendered = [
            item
            for item in project["artifacts"]
            if item.get("metadata", {}).get("lifecycle") == "music_video_render"
        ]
        self.assertEqual(len(rendered), 1)
        metadata = rendered[0]["metadata"]
        self.assertEqual(metadata["song_excerpt"], {"start_us": 0, "end_us": 20_000_000})
        self.assertEqual(len(metadata["visual_bindings"]), 2)
        self.assertEqual(metadata["visual_bindings"][0]["shot_id"], "mv_shot_01")
        self.assertEqual(metadata["visual_bindings"][1]["shot_id"], "mv_shot_02")
        self.assertEqual(metadata["lifecycle"], "music_video_render")

        review_heading = page.get_by_role(
            "heading", name="Финальная проверка музыкального клипа", exact=True
        )
        expect(review_heading).to_be_visible(timeout=60_000)
        review = review_heading.locator("xpath=ancestor::section[1]")
        expect(review.get_by_text("20–30 с: pass", exact=True).first).to_be_visible(timeout=60_000)
        review.get_by_role("button", name="Сохранить финальную проверку", exact=True).click()
        expect(review.get_by_text("Текущий вердикт:", exact=False)).to_contain_text("approved", timeout=60_000)

        workflow = _api_json("GET", f"/api/uv/projects/{encoded_id}/workflow")
        self.assertEqual(workflow["readiness"], "ready")
        self.assertIsNotNone(workflow["current_outcome"])
        self.assertEqual(workflow["current_outcome"]["artifact_id"], rendered[0]["id"])
        review_prerequisite = next(
            item for item in workflow["prerequisites"] if item["prerequisite_id"] == "music.review"
        )
        self.assertTrue(review_prerequisite["satisfied"])

        mutation_paths = [urllib.parse.urlparse(url).path for url in mutation_posts]
        workflow_action_paths = [path for path in mutation_paths if "/workflow/actions/" in path]
        self.assertEqual(
            workflow_action_paths,
            [],
            f"Music UI still used retired Product Orchestrator actions: observed={workflow_action_paths}",
        )
        expected_direct_paths = {
            f"/api/uv/projects/{encoded_id}/music-map/commands",
            f"/api/uv/projects/{encoded_id}/music-direction/commands",
            f"/api/uv/projects/{encoded_id}/music-assembly/commands",
            f"/api/uv/projects/{encoded_id}/capabilities/video.render_music_video/execute",
            f"/api/uv/projects/{encoded_id}/music-video-review",
        }
        observed_direct_paths = expected_direct_paths.intersection(mutation_paths)
        self.assertEqual(
            observed_direct_paths,
            expected_direct_paths,
            "Music UI did not exercise every established direct mutation authority: "
            f"missing={sorted(expected_direct_paths - observed_direct_paths)}; "
            f"observed={sorted(set(mutation_paths))}",
        )

        page.screenshot(path=str(self.artifact_dir / "stage7-music-video-final.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()
