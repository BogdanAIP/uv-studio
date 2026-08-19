"""Permanent product-workspace browser outcomes for the D-060 UX surface.

The older Stage 7/8 and editing suites remain durable real-media/API harnesses.
This module adapts only their browser-facing expectations to the current product
workspaces so release acceptance proves user outcomes without reintroducing
implementation vocabulary into the UI.
"""

from __future__ import annotations

import urllib.parse

from playwright.sync_api import Page, expect

import test_product_music_video_outcome as music_product
import test_product_user_outcomes as editing_product
import test_stage8_composition_outcomes as composition_harness
import test_stage8_outcomes as stage8_harness
import test_user_outcomes as base


class ProductBrowserUserOutcomes(editing_product.ProductBrowserUserOutcomes):
    """Keep the real editing/dubbing/continuity outcome on current product copy."""

    def _complete_dubbing(self, page: Page, project_id: str) -> None:
        source = self._source_reference(project_id)
        self._seed_reviewed_transcript(project_id, source["id"])

        page.get_by_test_id("workspace-dubbing").click()
        dubbing = page.get_by_text(
            "Проверьте текст, при необходимости переведите его", exact=False
        ).locator("xpath=ancestor::section[1]")
        expect(dubbing).to_be_visible(timeout=30_000)
        dubbing.get_by_role("button", name="Обновить", exact=True).click()

        source_select = dubbing.get_by_label("Видео для дубляжа", exact=True)
        base._select_option_containing(source_select, self.source_video.name)

        translation_card = dubbing.get_by_text("Текст и перевод", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        source_text = translation_card.get_by_role("paragraph").filter(has_text="hello world")
        expect(source_text).to_be_visible()
        translation_card.get_by_label("Перевод segment_1", exact=True).fill("привет мир")
        translation_card.get_by_role("button", name="Сохранить перевод", exact=True).click()
        expect(dubbing.get_by_text("Перевод сохранён.", exact=True)).to_be_visible()

        audio_card = dubbing.get_by_text("Речевая дорожка", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        audio_card.locator('input[type="file"][accept="audio/*"]').set_input_files(
            str(self.prepared_speech)
        )
        audio_select = audio_card.get_by_label("Речевая дорожка", exact=True)
        expect(audio_select.locator("option:checked")).to_have_text(
            self.prepared_speech.name, timeout=30_000
        )
        audio_card.get_by_role(
            "button", name="Привязать дорожку к тексту", exact=True
        ).click()
        expect(
            dubbing.get_by_text(
                "Речевая дорожка привязана к выбранному тексту.", exact=True
            )
        ).to_be_visible()

        review_card = dubbing.get_by_text("Проверка и применение", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        review_card.get_by_label(
            "Содержание и произношение проверены", exact=True
        ).check()
        review_card.get_by_label("Синхронизация с видео проверена", exact=True).check()
        review_card.get_by_role("button", name="Одобрить", exact=True).click()
        expect(review_card.get_by_text("Проверка пройдена", exact=True)).to_be_visible(
            timeout=45_000
        )
        expect(review_card.get_by_text("Синхронизация: норма", exact=False)).to_be_visible()
        review_card.get_by_role("button", name="Применить озвучку", exact=True).click()
        expect(dubbing.get_by_text("Озвучка применена.", exact=True)).to_be_visible()

        result = dubbing.get_by_text("Видео с применённой озвучкой", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        result.get_by_role("button", name="Собрать видео", exact=True).click()
        expect(result.get_by_text("Видео готово", exact=True)).to_be_visible(timeout=90_000)


class ProductMusicVideoBrowserOutcome(music_product.ProductMusicVideoBrowserOutcome):
    """Use the product test's own Playwright context without nesting Sync API loops."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The inherited fixture owns backend/frontend/media setup and also starts a
        # browser. The product test method intentionally owns its browser context,
        # so stop the fixture browser before entering its sync_playwright() block.
        if hasattr(cls, "browser"):
            cls.browser.close()
            delattr(cls, "browser")
        if hasattr(cls, "_playwright"):
            cls._playwright.stop()
            delattr(cls, "_playwright")


class ProductStage8CompositionBrowserOutcomes(
    composition_harness.Stage8CompositionBrowserOutcomes
):
    """Prove story, advertising and free-form preparation via product workspaces."""

    def test_story_commercial_and_free_workspaces_round_trip_through_ui(self) -> None:
        page = self._new_page()

        _story_id, story_encoded = self._create_project(
            "E2E Stage 8 Story", "story_video"
        )
        page.goto(f"/projects/{story_encoded}")
        expect(page.get_by_role("heading", name="История", exact=True)).to_be_visible()
        expect(
            page.get_by_role("heading", name="История и материалы", exact=True)
        ).to_be_visible()
        page.get_by_label("Stage 8 brief").fill(
            "Герой возвращается домой после долгого путешествия"
        )
        page.get_by_label("Stage 8 script").fill("Сцена 1. Герой входит в кадр.")
        page.locator('input[aria-label="Stage 8 workspace video"]').set_input_files(
            str(self.video)
        )
        expect(page.get_by_label(f"Использовать {self.video.name}")).to_be_checked(
            timeout=60_000
        )
        page.get_by_role("button", name="Сохранить подготовку", exact=True).click()
        expect(
            page.get_by_text("Подготовка проекта сохранена.", exact=True)
        ).to_be_visible(timeout=60_000)
        self._assert_workspace(story_encoded, "story_video", "video", "story_video")
        page.reload()
        expect(page.get_by_label("Stage 8 brief")).to_have_value(
            "Герой возвращается домой после долгого путешествия"
        )
        expect(page.get_by_label(f"Использовать {self.video.name}")).to_be_checked(
            timeout=60_000
        )

        _commercial_id, commercial_encoded = self._create_project(
            "E2E Stage 8 Commercial", "commercial_product"
        )
        page.goto(f"/projects/{commercial_encoded}")
        expect(page.get_by_role("heading", name="Реклама", exact=True)).to_be_visible()
        expect(
            page.get_by_role("heading", name="Задача и материалы продукта", exact=True)
        ).to_be_visible()
        page.get_by_label("Stage 8 brief").fill(
            "Показать продукт крупно и сохранить точные детали упаковки"
        )
        page.get_by_label("Stage 8 script").fill("Текст оффера без подмены продукта")
        page.locator('input[aria-label="Stage 8 workspace image"]').set_input_files(
            str(self.image)
        )
        expect(page.get_by_label(f"Использовать {self.image.name}")).to_be_checked(
            timeout=60_000
        )
        page.get_by_role("button", name="Сохранить подготовку", exact=True).click()
        expect(
            page.get_by_text("Подготовка проекта сохранена.", exact=True)
        ).to_be_visible(timeout=60_000)
        self._assert_workspace(
            commercial_encoded, "commercial_product", "image", "product_image"
        )
        page.reload()
        expect(page.get_by_label("Stage 8 script")).to_have_value(
            "Текст оффера без подмены продукта"
        )
        expect(page.get_by_label(f"Использовать {self.image.name}")).to_be_checked(
            timeout=60_000
        )

        _free_id, free_encoded = self._create_project(
            "E2E Stage 8 Free", "free_project"
        )
        page.goto(f"/projects/{free_encoded}")
        expect(page.get_by_role("heading", name="Подготовка", exact=True)).to_be_visible()
        expect(
            page.get_by_role("heading", name="Материалы и заметки", exact=True)
        ).to_be_visible()
        page.locator('input[aria-label="Stage 8 workspace audio"]').set_input_files(
            str(self.audio)
        )
        expect(page.get_by_label(f"Использовать {self.audio.name}")).to_be_checked(
            timeout=60_000
        )
        page.get_by_role("button", name="Сохранить подготовку", exact=True).click()
        expect(
            page.get_by_text("Подготовка проекта сохранена.", exact=True)
        ).to_be_visible(timeout=60_000)
        self._assert_workspace(free_encoded, "free_project", "audio", "audio")
        page.reload()
        expect(page.get_by_label("Stage 8 brief")).to_have_value("")
        expect(page.get_by_label(f"Использовать {self.audio.name}")).to_be_checked(
            timeout=60_000
        )

        page.screenshot(
            path=str(self.artifact_dir / "product-composition-workspaces.png"),
            full_page=True,
        )


class ProductStage8BrowserOutcomes(stage8_harness.Stage8BrowserOutcomes):
    """Prove local photo, visualizer and optional lip-sync product paths."""

    def test_photo_visualizer_and_optional_lipsync_user_paths(self) -> None:
        page = self._new_page()

        _photo_id, photo_encoded = self._create_project(
            "E2E Stage 8 Photo", "photo_to_video"
        )
        page.goto(f"/projects/{photo_encoded}")
        expect(page.get_by_role("heading", name="Фото → видео", exact=True)).to_be_visible()
        expect(
            page.get_by_role("heading", name="Собрать видео из фотографий", exact=True)
        ).to_be_visible()
        page.locator('input[aria-label="Изображения Stage 8"]').set_input_files(
            [str(self.red_image), str(self.blue_image)]
        )
        expect(page.get_by_text(self.red_image.name, exact=False).first).to_be_visible(
            timeout=60_000
        )
        expect(page.get_by_text(self.blue_image.name, exact=False).first).to_be_visible(
            timeout=60_000
        )
        page.get_by_role(
            "button", name="Опустить изображение 1", exact=True
        ).click()
        page.locator('input[aria-label="Аудио Stage 8"]').set_input_files(
            str(self.audio)
        )
        photo_audio = page.get_by_label("Аудио для фото-видео")
        expect(photo_audio).to_be_visible(timeout=60_000)
        base._select_option_containing(photo_audio, self.audio.name)
        page.get_by_role("button", name="Собрать видео", exact=True).click()
        expect(
            page.get_by_role("link", name="Открыть готовый рендер", exact=True)
        ).to_be_visible(timeout=120_000)

        photo_project = stage8_harness._api_json(
            "GET", f"/api/uv/projects/{photo_encoded}"
        )
        photo_artifacts = [
            item
            for item in photo_project["artifacts"]
            if item.get("metadata", {}).get("lifecycle") == "photo_to_video_render"
        ]
        self.assertEqual(len(photo_artifacts), 1)
        photo_images = {
            item.get("metadata", {}).get("original_name"): item["id"]
            for item in photo_project["sources"]
            if item["kind"] == "image"
        }
        self.assertEqual(
            [
                item["source_id"]
                for item in photo_artifacts[0]["metadata"]["image_bindings"]
            ],
            [photo_images[self.blue_image.name], photo_images[self.red_image.name]],
        )
        self.assertIsNotNone(photo_artifacts[0]["metadata"]["audio_binding"])

        _visualizer_id, visualizer_encoded = self._create_project(
            "E2E Stage 8 Visualizer", "visualizer"
        )
        page.goto(f"/projects/{visualizer_encoded}")
        expect(page.get_by_role("heading", name="Визуализатор", exact=True)).to_be_visible()
        expect(
            page.get_by_role("heading", name="Собрать аудиовизуализатор", exact=True)
        ).to_be_visible()
        page.locator('input[aria-label="Аудио Stage 8"]').set_input_files(
            str(self.audio)
        )
        visualizer_audio = page.get_by_label("Master-аудио визуализатора")
        expect(visualizer_audio).to_be_visible(timeout=60_000)
        base._select_option_containing(visualizer_audio, self.audio.name)
        page.locator('input[aria-label="Изображения Stage 8"]').set_input_files(
            str(self.blue_image)
        )
        artwork = page.get_by_label("Обложка визуализатора")
        expect(artwork).to_be_visible(timeout=60_000)
        base._select_option_containing(artwork, self.blue_image.name)
        page.get_by_role("button", name="Собрать визуализатор", exact=True).click()
        expect(
            page.get_by_role("link", name="Открыть готовый рендер", exact=True)
        ).to_be_visible(timeout=120_000)

        visualizer_project = stage8_harness._api_json(
            "GET", f"/api/uv/projects/{visualizer_encoded}"
        )
        visualizer_artifacts = [
            item
            for item in visualizer_project["artifacts"]
            if item.get("metadata", {}).get("lifecycle")
            == "audio_visualizer_render"
        ]
        self.assertEqual(len(visualizer_artifacts), 1)
        self.assertIsNotNone(
            visualizer_artifacts[0]["metadata"]["artwork_binding"]
        )
        self.assertEqual(
            visualizer_artifacts[0]["metadata"]["audio_binding"]["source_id"],
            next(
                item["id"]
                for item in visualizer_project["sources"]
                if item["kind"] == "audio"
            ),
        )

        _performance_id, performance_encoded = self._create_project(
            "E2E Stage 8 Performance", "performance_lip_sync"
        )
        page.goto(f"/projects/{performance_encoded}")
        expect(page.get_by_role("heading", name="Lip-sync", exact=True)).to_be_visible()
        expect(
            page.get_by_role("heading", name="Портрет + речь → lip-sync", exact=True)
        ).to_be_visible()
        expect(page.get_by_text("Нужен локальный модуль", exact=True)).to_be_visible(
            timeout=60_000
        )
        page.locator('input[aria-label="Портрет lip-sync"]').set_input_files(
            str(self.red_image)
        )
        performance_portrait = page.get_by_label("Выбранный портрет lip-sync")
        base._select_option_containing(performance_portrait, self.red_image.name)
        page.locator('input[aria-label="Готовая речь lip-sync"]').set_input_files(
            str(self.audio)
        )
        performance_speech = page.get_by_label("Выбранная речь lip-sync")
        base._select_option_containing(performance_speech, self.audio.name)
        expect(page.get_by_text("Нужен локальный модуль", exact=True)).to_be_visible(
            timeout=60_000
        )
        expect(
            page.get_by_role("button", name="Выполнить lip-sync", exact=True)
        ).to_be_disabled()

        performance_project = stage8_harness._api_json(
            "GET", f"/api/uv/projects/{performance_encoded}"
        )
        self.assertEqual(
            sorted(item["kind"] for item in performance_project["sources"]),
            ["audio", "image"],
        )
        self.assertEqual(
            [
                item
                for item in performance_project["artifacts"]
                if item.get("metadata", {}).get("lifecycle")
                == "performance_lip_sync_render"
            ],
            [],
        )

        page.screenshot(
            path=str(self.artifact_dir / "product-additional-recipes-final.png"),
            full_page=True,
        )
