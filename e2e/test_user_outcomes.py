"""Real browser user-outcome coverage for the Stage 4C, Stage 5 and Stage 6 surfaces.

The suite runs the built Next.js frontend against the real UV Studio FastAPI app,
uses real FFmpeg media fixtures, and drives user-visible workflow controls with
Playwright Chromium. Optional ASR/provider/VLM execution is not a browser-test
precondition: provider-independent fixture setup uses UV-owned semantic APIs,
while targeted edit, dubbing and linked-shot continuity Review/Accept flows are
completed through the production UI.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
BACKEND_ORIGIN = "http://127.0.0.1:8000"
FRONTEND_ORIGIN = "http://127.0.0.1:3000"


class ProcessHandle:
    def __init__(self, process: subprocess.Popen[Any], log_path: Path, log_handle: Any) -> None:
        self.process = process
        self.log_path = log_path
        self.log_handle = log_handle

    def stop(self) -> None:
        if self.process.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    self.process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.log_handle.close()

    def tail(self) -> str:
        try:
            text = self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return text[-12_000:]


def _start_process(command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> ProcessHandle:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    kwargs: dict[str, Any] = {
        "cwd": cwd,
        "env": env,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    return ProcessHandle(process, log_path, log_handle)


def _wait_http(url: str, process: ProcessHandle, *, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.process.poll() is not None:
            raise AssertionError(
                f"process exited before {url} became ready (code {process.process.returncode})\n"
                f"{process.tail()}"
            )
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                if 200 <= response.status < 400:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        time.sleep(0.35)
    raise AssertionError(f"{url} did not become ready: {last_error!r}\n{process.tail()}")


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
        raise AssertionError(f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}")


def _ffmpeg_fixture(path: Path, *, duration: float, color: str, tone_hz: int) -> None:
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
            f"color=c={color}:s=640x360:r=30:d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={tone_hz}:sample_rate=48000:duration={duration}",
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


def _speech_fixture(path: Path) -> None:
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
            "sine=frequency=440:sample_rate=48000:duration=1",
            "-filter:a",
            "volume=0.05",
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
    with urllib.request.urlopen(request, timeout=30.0) as response:
        return json.loads(response.read().decode("utf-8"))


def _project_path(project_id: str, suffix: str) -> str:
    encoded = urllib.parse.quote(project_id, safe="")
    return f"/api/uv/projects/{encoded}{suffix}"


def _card_for(page_or_section: Any, title: str):
    return page_or_section.get_by_text(title, exact=True).locator(
        "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
    )


def _select_option_containing(select: Any, needle: str) -> None:
    option = select.locator("option").filter(has_text=needle).first
    option.wait_for(state="attached", timeout=60_000)
    value = option.get_attribute("value")
    if not value:
        raise AssertionError(f"select option containing {needle!r} had no value")
    select.select_option(value=value)


class BrowserUserOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise unittest.SkipTest("real browser E2E requires FFmpeg/FFprobe")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if npm is None:
            raise unittest.SkipTest("real browser E2E requires npm")

        cls._tmp = tempfile.TemporaryDirectory(prefix="uv-studio-browser-e2e-")
        cls.temp_root = Path(cls._tmp.name)
        cls.artifact_dir = Path(
            os.environ.get("UV_E2E_ARTIFACT_DIR", str(ROOT / "e2e-artifacts"))
        ).resolve()
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)

        cls.source_video = cls.temp_root / "source-e2e.mp4"
        cls.replacement_video = cls.temp_root / "replacement-e2e.mp4"
        cls.prepared_speech = cls.temp_root / "prepared-speech-e2e.wav"
        _ffmpeg_fixture(cls.source_video, duration=6.0, color="blue", tone_hz=220)
        _ffmpeg_fixture(cls.replacement_video, duration=2.0, color="red", tone_hz=330)
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
            log_path=cls.artifact_dir / "backend.log",
        )
        try:
            _wait_http(f"{BACKEND_ORIGIN}/api/health", cls.backend)
            cls.frontend = _start_process(
                [npm, "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000"],
                cwd=FRONTEND,
                env=env,
                log_path=cls.artifact_dir / "frontend.log",
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

    def _create_project(self, page: Page) -> str:
        page.goto("/projects")
        expect(page.get_by_role("heading", name="Проекты", exact=True)).to_be_visible()
        title = "E2E Stage 4C + Stage 5 + Stage 6"
        page.get_by_placeholder("Название нового проекта").fill(title)
        page.get_by_role("button", name="Создать проект", exact=True).click()
        project_title = page.get_by_text(title, exact=True)
        expect(project_title).to_be_visible()
        project_title.click()
        page.wait_for_url("**/projects/*")
        project_id = urllib.parse.unquote(urllib.parse.urlsplit(page.url).path.rsplit("/", 1)[-1])
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        return project_id

    def _create_project_via_api(self, page: Page, *, title: str, recipe_id: str) -> str:
        project = _api_json(
            "POST",
            "/api/uv/projects",
            {"title": title, "recipe_id": recipe_id},
        )
        project_id = project["project_id"]
        page.goto(f"/projects/{urllib.parse.quote(project_id, safe='')}")
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        return project_id

    def _upload_editor_video(self, page: Page, path: Path) -> None:
        picker = page.locator('input[type="file"][accept^="video"]')
        expect(picker).to_have_count(1)
        picker.set_input_files(str(path))
        expect(page.get_by_text(path.name, exact=True).first).to_be_visible(timeout=45_000)

    def _select_original_source(self, page: Page) -> None:
        source_button = page.get_by_role("button").filter(has_text=self.source_video.name).first
        expect(source_button).to_be_visible()
        source_button.click()
        expect(page.get_by_text(self.source_video.name, exact=True).first).to_be_visible()

    def _select_range(self, page: Page) -> None:
        track = page.locator("div.cursor-crosshair.bg-slate-950").first
        expect(track).to_be_visible()
        track.scroll_into_view_if_needed()
        box = track.bounding_box()
        self.assertIsNotNone(box)
        assert box is not None
        y = box["y"] + min(45.0, box["height"] / 2)
        page.mouse.move(box["x"] + 80.0, y)
        page.mouse.down()
        page.mouse.move(box["x"] + 240.0, y, steps=8)
        page.mouse.up()
        expect(page.get_by_text("Начало:", exact=False)).to_contain_text("00:01.000")
        expect(page.get_by_text("Конец:", exact=False)).to_contain_text("00:03.000")

    def _complete_targeted_edit(self, page: Page) -> None:
        self._select_original_source(page)
        self._select_range(page)
        page.locator("#uv-change-request").fill(
            "Заменить выбранные две секунды подготовленным клипом, не изменяя материал за границами диапазона."
        )
        page.get_by_role("button", name="Подготовить изменение", exact=True).click()
        expect(page.get_by_text("Brief сохранён", exact=True)).to_be_visible(timeout=30_000)

        page.get_by_role("button", name="Подготовить вариант замены", exact=True).click()
        result_selects = page.locator('select[aria-label^="Результат "]')
        expect(result_selects.first).to_be_visible(timeout=45_000)
        count = result_selects.count()
        self.assertGreater(count, 0, "replacement Review must expose at least one ReviewTarget")
        for index in range(count):
            outcome = result_selects.nth(index)
            outcome.select_option("pass")
            target_card = outcome.locator(
                "xpath=ancestor::div[contains(@class,'rounded-xl')][1]"
            )
            target_card.locator("textarea").fill(
                "Browser E2E подтверждает критерий по показанному full candidate."
            )

        page.get_by_role("button", name="Одобрить вариант", exact=True).click()
        expect(page.get_by_text("Проверка: вариант одобрен", exact=True)).to_be_visible()
        page.get_by_role("button", name="Принять в timeline", exact=True).click()
        expect(page.get_by_text("Правка принята через D-032", exact=False)).to_be_visible()

        render_section = page.get_by_text(
            "Собрать принятые правки в один мастер", exact=True
        ).locator("xpath=ancestor::section[1]")
        render_section.get_by_role("button", name="Собрать мастер", exact=True).click()
        expect(
            render_section.get_by_text(
                "Мастер соответствует текущему Accepted state", exact=True
            )
        ).to_be_visible(timeout=90_000)

    def _source_reference(self, project_id: str) -> dict[str, Any]:
        state = _api_json("GET", _project_path(project_id, "/editor/state"))
        for source in state["sources"]:
            if source.get("metadata", {}).get("original_name") == self.source_video.name:
                return source
        self.fail("original E2E source was not present in canonical editor state")

    def _seed_reviewed_transcript(self, project_id: str, source_id: str) -> None:
        result = _api_json(
            "POST",
            _project_path(project_id, "/editor/commands"),
            {
                "command": "import_dubbing_transcript",
                "source_id": source_id,
                "language": "en",
                "start_us": 4_000_000,
                "end_us": 5_500_000,
                "segments": [
                    {
                        "segment_id": "segment_1",
                        "start_us": 4_000_000,
                        "end_us": 5_500_000,
                        "text": "hello world",
                        "speaker_label": "speaker_1",
                        "confidence": 1.0,
                    }
                ],
            },
        )
        self.assertEqual(result["command"], "import_dubbing_transcript")

    def _complete_dubbing(self, page: Page, project_id: str) -> None:
        source = self._source_reference(project_id)
        self._seed_reviewed_transcript(project_id, source["id"])

        dubbing = page.get_by_text(
            "Дубляж в том же проекте и таймлайне", exact=True
        ).locator("xpath=ancestor::section[1]")
        dubbing.get_by_role("button", name="Перечитать состояние", exact=True).click()

        source_card = _card_for(dubbing, "Источник и распознавание")
        source_card.locator("select").first.select_option(label=self.source_video.name)

        translation_card = _card_for(dubbing, "Transcript и перевод")
        expect(
            translation_card.get_by_role("paragraph").filter(has_text="hello world")
        ).to_be_visible()
        translation_card.locator("textarea").first.fill("привет мир")
        translation_card.get_by_role("button", name="Сохранить перевод", exact=True).click()
        expect(dubbing.get_by_text("Перевод сохранён и привязан", exact=False)).to_be_visible()

        audio_card = _card_for(dubbing, "Подготовленная речь")
        audio_picker = audio_card.locator('input[type="file"][accept="audio/*"]')
        audio_picker.set_input_files(str(self.prepared_speech))
        expect(
            audio_card.locator("select").first.locator("option:checked")
        ).to_have_text(self.prepared_speech.name, timeout=30_000)
        audio_card.get_by_role("button", name="Привязать к тексту и диапазону", exact=True).click()
        expect(dubbing.get_by_text("Голосовая дорожка привязана", exact=False)).to_be_visible()

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
        expect(dubbing.get_by_text("Одобренная озвучка принята", exact=False)).to_be_visible()

        dubbing_render = dubbing.get_by_text(
            "Материализовать видео + принятый дубляж", exact=True
        ).locator("xpath=ancestor::div[contains(@class,'rounded-2xl')][1]")
        dubbing_render.get_by_role("button", name="Собрать мастер", exact=True).click()
        expect(dubbing_render.get_by_text("Мастер с принятой озвучкой", exact=True)).to_be_visible(
            timeout=90_000
        )

    def _complete_sequence_continuity(self, page: Page, project_id: str) -> None:
        optional_panel = page.get_by_text(
            "Непрерывность связанных кадров", exact=True
        ).locator("xpath=ancestor::section[1]")
        expect(optional_panel.get_by_text("Stage 6 · необязательно", exact=True)).to_be_visible()
        optional_panel.get_by_role("button", name="Включить последовательность", exact=True).click()

        sequence = page.get_by_text(
            "Принятый дубль → следующий связанный кадр", exact=True
        ).locator("xpath=ancestor::section[1]")
        expect(sequence).to_be_visible(timeout=30_000)

        sequence.get_by_label("Замысел связанного кадра", exact=True).fill(
            "Зафиксировать первый factual anchor для следующего связанного кадра."
        )
        sequence.get_by_label("Фиксированное условие непрерывности", exact=True).fill(
            "Сохранить идентичность субъекта и направление движения вправо."
        )
        sequence.get_by_role("button", name="Сохранить план кадра", exact=True).click()
        expect(
            sequence.get_by_label("Кадр для подготовленного дубля", exact=True).locator("option:checked")
        ).to_contain_text("shot_01", timeout=30_000)

        video_select = sequence.get_by_label("Видео для подготовленного дубля", exact=True)
        _select_option_containing(video_select, self.source_video.name)
        sequence.get_by_role("button", name="Зарегистрировать дубль", exact=True).click()
        take_select = sequence.get_by_label("Дубль последовательности", exact=True)
        expect(take_select.locator("option:checked")).to_contain_text("shot_01", timeout=30_000)
        expect(take_select.locator("option:checked")).to_contain_text("prepared")

        sequence.get_by_role("button", name="Показать контекст границы", exact=True).click()
        boundary = sequence.get_by_text("3. Bounded TimelineContext", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-xl')][1]"
        )
        expect(boundary.get_by_text("Первый кадр последовательности не требует опоры.", exact=True)).to_be_visible()
        expect(boundary.get_by_text("Проверяемый дубль · начало", exact=True)).to_be_visible()

        sequence.get_by_label("Результат shot_01.continuity", exact=True).select_option("pass")
        sequence.get_by_label("Наблюдение по принятому дублю", exact=True).fill(
            "Subject exits screen-right."
        )
        sequence.get_by_label("Вердикт Review последовательности", exact=True).select_option("approved")
        sequence.get_by_role("button", name="Сохранить Review", exact=True).click()
        expect(sequence.get_by_text("Текущий Review: Одобрить", exact=True)).to_be_visible(timeout=30_000)
        sequence.get_by_role("button", name="Accept дубль", exact=True).click()
        expect(sequence.get_by_text("Дубль принят и может стать factual anchor.", exact=True)).to_be_visible(timeout=30_000)
        first_anchor_id = take_select.input_value()
        self.assertTrue(first_anchor_id)
        anchor_button = sequence.get_by_role("button", name="Сделать опорой", exact=True)
        anchor_button.click()
        anchor_stat = sequence.get_by_text("Текущая опора", exact=True).locator("xpath=parent::div")
        expect(anchor_stat).to_contain_text(first_anchor_id, timeout=30_000)

        state_after_anchor = _api_json("GET", _project_path(project_id, "/sequence/state"))
        sequence_state = state_after_anchor["sequences"][0]
        self.assertEqual(sequence_state["anchor_take_id"], first_anchor_id)

        sequence.get_by_label("Замысел связанного кадра", exact=True).fill(
            "Продолжить принятый выход вправо в более крупном втором кадре."
        )
        sequence.get_by_label("Фиксированное условие непрерывности", exact=True).fill(
            "Продолжить screen-right направление принятой опоры."
        )
        sequence.get_by_label("Разрешённое изменение непрерывности", exact=True).fill(
            "Разрешить более крупное кадрирование."
        )
        sequence.get_by_role("button", name="Сохранить план кадра", exact=True).click()
        expect(
            sequence.get_by_label("Кадр для подготовленного дубля", exact=True).locator("option:checked")
        ).to_contain_text("shot_02", timeout=30_000)

        _select_option_containing(video_select, self.replacement_video.name)
        sequence.get_by_role("button", name="Зарегистрировать дубль", exact=True).click()
        expect(take_select.locator("option:checked")).to_contain_text("shot_02", timeout=30_000)
        expect(take_select.locator("option:checked")).to_contain_text("prepared")

        sequence.get_by_role("button", name="Показать контекст границы", exact=True).click()
        expect(boundary.get_by_text("Принятая опора · хвост", exact=True)).to_be_visible(timeout=30_000)
        expect(boundary.get_by_text("Проверяемый дубль · начало", exact=True)).to_be_visible()
        expect(boundary.locator("video")).to_have_count(2)

        current_state = _api_json("GET", _project_path(project_id, "/sequence/state"))
        current_sequence = current_state["sequences"][0]
        prepared_take = next(
            take
            for take in current_sequence["takes"]
            if take["shot_id"] == "shot_02" and take["status"] == "prepared"
        )
        observed_context = _api_json(
            "GET",
            _project_path(
                project_id,
                f"/sequence/{urllib.parse.quote(current_sequence['sequence_id'], safe='')}/takes/{urllib.parse.quote(prepared_take['take_id'], safe='')}/context?window_us=1000000&samples=3",
            ),
        )
        self.assertEqual(observed_context["anchor"]["take_id"], first_anchor_id)
        self.assertEqual(
            observed_context["anchor"]["observations"][0]["statement"],
            "Subject exits screen-right.",
        )
        self.assertEqual(len(observed_context["anchor"]["sample_times_us"]), 3)
        self.assertEqual(len(observed_context["candidate"]["sample_times_us"]), 3)

        sequence.get_by_label("Результат shot_02.continuity", exact=True).select_option("pass")
        sequence.get_by_label("Наблюдение по принятому дублю", exact=True).fill(
            "Candidate continues the accepted screen-right direction."
        )
        sequence.get_by_label("Вердикт Review последовательности", exact=True).select_option("approved")
        sequence.get_by_role("button", name="Сохранить Review", exact=True).click()
        expect(sequence.get_by_text("Текущий Review: Одобрить", exact=True)).to_be_visible(timeout=30_000)
        sequence.get_by_role("button", name="Accept дубль", exact=True).click()
        expect(sequence.get_by_text("Дубль принят и может стать factual anchor.", exact=True)).to_be_visible(timeout=30_000)
        second_anchor_id = take_select.input_value()
        self.assertTrue(second_anchor_id)
        anchor_button = sequence.get_by_role("button", name="Сделать опорой", exact=True)
        anchor_button.click()
        expect(anchor_stat).to_contain_text(second_anchor_id, timeout=30_000)

        final_state = _api_json("GET", _project_path(project_id, "/sequence/state"))["sequences"][0]
        accepted = [take for take in final_state["takes"] if take["status"] == "accepted"]
        self.assertEqual(len(accepted), 2)
        self.assertEqual(final_state["anchor_take_id"], second_anchor_id)
        self.assertNotEqual(final_state["anchor_take_id"], first_anchor_id)

    def test_targeted_edit_isolated_while_dubbing_and_sequence_regressions_remain_operable(self) -> None:
        page = self._new_page()
        try:
            targeted_project_id = self._create_project_via_api(
                page,
                title="E2E Targeted Edit",
                recipe_id="free_project",
            )
            expect(
                page.get_by_role("heading", name="Точечное редактирование исходного видео", exact=True)
            ).to_be_visible()
            expect(page.get_by_text("Дубляж в том же проекте и таймлайне", exact=True)).to_have_count(0)
            expect(page.get_by_text("Непрерывность связанных кадров", exact=True)).to_have_count(0)
            self._upload_editor_video(page, self.source_video)
            self._upload_editor_video(page, self.replacement_video)
            self._complete_targeted_edit(page)

            regression_project_id = self._create_project_via_api(
                page,
                title="E2E Dubbing + Continuity",
                recipe_id="general_video",
            )
            self._upload_editor_video(page, self.source_video)
            self._upload_editor_video(page, self.replacement_video)
            expect(page.get_by_text("Дубляж в том же проекте и таймлайне", exact=True)).to_be_visible()
            expect(page.get_by_text("Непрерывность связанных кадров", exact=True)).to_be_visible()
            self._complete_dubbing(page, regression_project_id)
            self._complete_sequence_continuity(page, regression_project_id)

            report = {
                "targeted_edit_project_id": targeted_project_id,
                "dubbing_continuity_project_id": regression_project_id,
                "targeted_edit": "accepted_and_rendered",
                "dubbing": "accepted_and_rendered",
                "sequence_continuity": "two_linked_takes_accepted_and_reanchored",
                "routing": "targeted_edit_isolated_from_dubbing_and_continuity",
                "frontend": FRONTEND_ORIGIN,
            }
            (self.artifact_dir / "user-outcomes.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception:
            page.screenshot(path=str(self.artifact_dir / "failure.png"), full_page=True)
            raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
