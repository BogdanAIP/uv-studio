"""Browser evidence for the Product Orchestrator General Video workspace.

This is Class B informed regression evidence, not Class C cold-start acceptance: the
General Video recipe itself is selected through a UV-owned setup API. From the empty
project onward, brief entry, image/video import, workspace save and final render are
driven only through visible production UI controls.
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
        "-f", "lavfi", "-i", "color=c=navy:s=640x360:d=0.04",
        "-frames:v", "1", "-update", "1", str(path),
    ])


def _video_fixture(path: Path) -> None:
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=1.2",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ])


class GeneralVideoBrowserOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise unittest.SkipTest("General Video browser E2E requires FFmpeg/FFprobe")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("General Video browser E2E requires npm")
        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-general-video-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)
        cls.image = cls.temp_root / "general-frame.png"
        cls.video = cls.temp_root / "general-clip.mp4"
        _image_fixture(cls.image)
        _video_fixture(cls.video)
        env = os.environ.copy()
        env.update({
            "PYTHONUNBUFFERED": "1",
            "NEXT_TELEMETRY_DISABLED": "1",
            "UV_STUDIO_PROJECTS_DIR": str(cls.temp_root / "projects"),
            "UV_STUDIO_CONFIG_DIR": str(cls.temp_root / "config"),
        })
        cls.backend = _start_process(
            [sys.executable, "-m", "uv_studio.server"], cwd=ROOT, env=env,
            log_path=cls.artifact_dir / "general-video-backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND, env=env,
                log_path=cls.artifact_dir / "general-video-frontend.log",
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
        context = self.browser.new_context(base_url=FRONTEND_ORIGIN, viewport={"width": 1600, "height": 1200}, locale="ru-RU")
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(60_000)
        return page

    def test_general_workspace_reaches_current_master_from_visible_inputs(self) -> None:
        page = self._new_page()
        title = "General Video E2E"
        project = _api_json("POST", "/api/uv/projects", {"title": title, "recipe_id": "general_video"})
        project_id = project["project_id"]
        encoded = urllib.parse.quote(project_id, safe="")
        page.goto(f"/projects/{encoded}")
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Обычный видеоролик", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Сборка текущего визуального ряда", exact=True)).to_be_visible()
        page.get_by_label("Stage 8 brief").fill("Собрать короткий ролик из изображения и клипа")
        page.locator('input[aria-label="Stage 8 workspace image"]').set_input_files(str(self.image))
        expect(page.get_by_label(f"Использовать {self.image.name}")).to_be_checked(timeout=60_000)
        page.locator('input[aria-label="Stage 8 workspace video"]').set_input_files(str(self.video))
        expect(page.get_by_label(f"Использовать {self.video.name}")).to_be_checked(timeout=60_000)
        expect(page.get_by_text("Порядок визуального ряда", exact=True)).to_be_visible()
        page.get_by_role("button", name="Сохранить рабочее пространство", exact=True).click()
        expect(page.get_by_text("Рабочее пространство сохранено с точной SHA-привязкой выбранных материалов.", exact=True)).to_be_visible(timeout=60_000)
        render_button = page.get_by_role("button", name="Собрать обычный видеоролик", exact=True)
        expect(render_button).to_be_enabled(timeout=60_000)
        render_button.click()
        expect(page.get_by_text("Текущий мастер соответствует входам", exact=True)).to_be_visible(timeout=120_000)
        workflow = _api_json("GET", _project_path(project_id, "/workflow"))
        self.assertEqual(workflow["recipe_id"], "general_video")
        self.assertEqual([item["workspace_id"] for item in workflow["relevant_workspaces"]], ["general_video"])
        self.assertIsNotNone(workflow["current_outcome"])
        metadata = workflow["current_outcome"]["metadata"]
        self.assertEqual(metadata["lifecycle"], "general_video_render")
        self.assertEqual(metadata["composition_mode"], "general_workspace_ordered_visuals")
        self.assertEqual([item["kind"] for item in metadata["visual_bindings"]], ["image", "video"])
        self.assertTrue(metadata["visual_bindings"][1]["embedded_audio_ignored"])
        self.assertIsNone(metadata["audio_binding"])
        page.screenshot(path=str(self.artifact_dir / "general-video-outcome.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()
