"""Music-video browser outcome through the Stage 9 product workspace."""

from __future__ import annotations

from pathlib import Path
import urllib.parse

from playwright.sync_api import expect, sync_playwright

import test_music_video_outcome as legacy
import test_user_outcomes as base


class ProductMusicVideoBrowserOutcome(legacy.MusicVideoBrowserOutcome):
    def _media_fixture(self, suffixes: set[str], *, exclude: set[Path] | None = None) -> Path:
        excluded = exclude or set()
        candidates: list[Path] = []
        for name in dir(self):
            try:
                value = getattr(self, name)
            except Exception:
                continue
            if isinstance(value, Path) and value.is_file() and value.suffix.lower() in suffixes and value not in excluded:
                candidates.append(value)
        if not candidates:
            self.fail(f"legacy music fixture did not expose a file with suffixes {sorted(suffixes)}")
        return sorted(candidates, key=lambda path: path.name)[0]

    def test_music_video_product_workspace_end_to_end(self) -> None:
        audio = self._media_fixture({".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"})
        first_video = self._media_fixture({".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"})
        second_video = self._media_fixture({".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}, exclude={first_video})

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(base_url="http://127.0.0.1:3000")
            try:
                page.goto("/projects")
                page.get_by_test_id("recipe-music_video").click()
                page.get_by_placeholder("Название нового проекта").fill("E2E музыкальный клип")
                page.get_by_role("button", name="Создать проект", exact=True).click()
                page.wait_for_url("**/projects/*")
                project_id = urllib.parse.unquote(page.url.rsplit("/", 1)[-1])

                expect(page.get_by_role("heading", name="Музыкальный клип", exact=True)).to_be_visible()
                planning = page.get_by_role("heading", name="Музыка и режиссура", exact=True).locator("xpath=ancestor::section[1]")
                expect(planning).to_be_visible()
                expect(page.get_by_text("Stage 7", exact=False)).to_have_count(0)
                expect(page.get_by_text("Project Store", exact=False)).to_have_count(0)

                planning.get_by_label("Файл песни", exact=True).set_input_files(str(audio))
                expect(planning.get_by_role("button", name="Сохранить разметку музыки", exact=True)).to_be_enabled(timeout=30_000)
                planning.get_by_label("Начало музыкального фрагмента", exact=True).fill("1")
                planning.get_by_label("Конец музыкального фрагмента", exact=True).fill("5")

                planning.get_by_role("button", name="Добавить секцию", exact=True).click()
                planning.get_by_label("Тип музыкальной секции 1", exact=True).select_option("verse")
                planning.get_by_label("Название музыкальной секции 1", exact=True).fill("Куплет")
                planning.get_by_label("Начало музыкальной секции 1", exact=True).fill("1")
                planning.get_by_label("Конец музыкальной секции 1", exact=True).fill("5")

                planning.get_by_role("button", name="Добавить маркер", exact=True).click()
                planning.get_by_label("Тип музыкального маркера 1", exact=True).select_option("cut_point")
                planning.get_by_label("Время музыкального маркера 1", exact=True).fill("3")
                planning.get_by_role("button", name="Сохранить разметку музыки", exact=True).click()
                expect(planning.get_by_text("Разметка музыки сохранена.", exact=True)).to_be_visible(timeout=30_000)

                music_map = base._api_json("GET", base._project_path(project_id, "/music-video/map"))
                self.assertEqual(music_map["excerpt"], {"start_us": 1_000_000, "end_us": 5_000_000})
                self.assertEqual(len(music_map["sections"]), 1)
                self.assertEqual(music_map["markers"][0]["kind"], "cut_point")

                planning.get_by_role("button", name="Создать черновик кадров", exact=True).click()
                intents = planning.locator('textarea[aria-label^="Замысел музыкального кадра "]')
                expect(intents).to_have_count(2)
                intents.nth(0).fill("Кадр A на первую половину куплета")
                intents.nth(1).fill("Кадр B после музыкального акцента")
                planning.get_by_role("button", name="Сохранить режиссёрский план", exact=True).click()
                direction = base._api_json("GET", base._project_path(project_id, "/music-video/direction"))
                self.assertEqual(len(direction["shots"]), 2)
                self.assertEqual(direction["shots"][0]["start_us"], 1_000_000)
                self.assertEqual(direction["shots"][0]["end_us"], 3_000_000)
                self.assertEqual(direction["shots"][1]["start_us"], 3_000_000)
                self.assertEqual(direction["shots"][1]["end_us"], 5_000_000)

                page.get_by_role("button", name="Сборка", exact=True).click()
                assembly = page.get_by_role("heading", name="Визуалы и сборка", exact=True).locator("xpath=ancestor::section[1]")
                assembly.get_by_label("Видео для Music Assembly", exact=True).set_input_files(str(first_video))
                assembly.get_by_label("Видео для Music Assembly", exact=True).set_input_files(str(second_video))
                first_select = assembly.get_by_label("Видеоисточник музыкального кадра 1", exact=True)
                second_select = assembly.get_by_label("Видеоисточник музыкального кадра 2", exact=True)
                base._select_option_containing(first_select, first_video.name)
                base._select_option_containing(second_select, second_video.name)
                assembly.get_by_label("Начало источника музыкального кадра 1", exact=True).fill("0")
                assembly.get_by_label("Начало источника музыкального кадра 2", exact=True).fill("0")
                assembly.get_by_role("button", name="Сохранить визуалы", exact=True).click()
                expect(assembly.get_by_text("Визуалы привязаны к кадрам.", exact=True)).to_be_visible(timeout=30_000)
                assembly_state = base._api_json("GET", base._project_path(project_id, "/music-video/assembly"))
                self.assertEqual(len(assembly_state["bindings"]), 2)

                assembly.get_by_role("button", name="Собрать клип", exact=True).click()
                expect(assembly.get_by_role("link", name="Открыть готовый клип", exact=True)).to_be_visible(timeout=90_000)

                page.get_by_role("button", name="Проверка", exact=True).click()
                review = page.get_by_role("heading", name="Проверка клипа", exact=True).locator("xpath=ancestor::section[1]")
                expect(review.get_by_label("Финальный Music Video рендер", exact=True)).to_be_visible(timeout=30_000)
                review.get_by_label("Вердикт финальной Music Video проверки", exact=True).select_option("needs_revision")
                review.get_by_label("Проверка переходов Music Video", exact=True).select_option("pass")
                review.get_by_label("Заметка финальной Music Video проверки", exact=True).fill("Browser E2E проверил итоговую версию и переходы.")
                review.get_by_role("button", name="Сохранить проверку", exact=True).click()
                expect(review.get_by_text("Текущая версия отправлена на доработку", exact=True)).to_be_visible(timeout=30_000)
                review_state = base._api_json("GET", base._project_path(project_id, "/music-video/review"))
                self.assertEqual(review_state["verdict"], "needs_revision")
                self.assertEqual(review_state["transition_outcome"], "pass")
            finally:
                browser.close()


# Keep the legacy class for its service/media fixture setup, but do not collect
# its copy-specific browser test methods from this product module.
for _name in dir(legacy.MusicVideoBrowserOutcome):
    if _name.startswith("test_"):
        setattr(ProductMusicVideoBrowserOutcome, _name, None)
# Rebind the product outcome after suppressing inherited tests.
ProductMusicVideoBrowserOutcome.test_music_video_product_workspace_end_to_end = ProductMusicVideoBrowserOutcome.__dict__["test_music_video_product_workspace_end_to_end"]
