"""Class C cold-start browser evidence from a user-equivalent clean state.

This suite deliberately avoids direct Project Store access, hidden workflow seeding
and semantic API setup. Projects are discovered, created, opened and completed
through the same visible product controls available to a clean-state user.
"""

from __future__ import annotations

import json

from playwright.sync_api import expect

import test_stage8_outcomes as stage8
from test_user_outcomes import _select_option_containing


class ClassCColdStartBrowserOutcome(stage8.Stage8BrowserOutcomes):
    # This class reuses only the clean application/media fixture bootstrap from
    # Stage8BrowserOutcomes. Its historical API-created Stage 8 scenario remains
    # covered by the parent test module and must not be inherited here.
    test_photo_and_visualizer_user_paths = None

    def _create_from_visible_catalog(self, page, *, recipe_title: str, project_title: str) -> None:
        page.goto("/")
        page.wait_for_url("**/projects")
        expect(page.get_by_role("heading", name="Проекты", exact=True)).to_be_visible()
        expect(page.get_by_text("Что нужно сделать?", exact=True)).to_be_visible()

        # Preserved-only compatibility recipes must stay out of clean-state
        # discovery. This proves the user is not asked to understand internal
        # workflow migration state before choosing a supported task.
        for hidden_title in ("Перенос движения", "Говорящий персонаж", "Performance / lip-sync"):
            expect(page.get_by_role("button", name=hidden_title, exact=False)).to_have_count(0)

        recipe = page.get_by_role("button", name=recipe_title, exact=False)
        expect(recipe).to_be_visible()
        recipe.click()
        expect(recipe.get_by_text("Выбрано", exact=True)).to_be_visible()

        title_input = page.get_by_placeholder("Название нового проекта")
        title_input.fill(project_title)
        create_button = page.get_by_role("button", name="Создать проект", exact=True)
        expect(create_button).to_be_enabled()
        create_button.click()

        project_link = page.get_by_role("link", name=project_title, exact=False)
        expect(project_link).to_be_visible(timeout=30_000)
        project_link.click()
        page.wait_for_url("**/projects/*")
        expect(page.get_by_role("heading", name=project_title, exact=True)).to_be_visible()
        expect(page.get_by_text("Product Orchestrator", exact=True)).to_be_visible()

    def test_clean_user_discovers_creates_and_completes_local_supported_tasks(self) -> None:
        page = self._new_page()

        self._create_from_visible_catalog(
            page,
            recipe_title="Фото в видео",
            project_title="Class C — фото в видео",
        )
        expect(page.get_by_role("heading", name="Фотографии → видео", exact=True)).to_be_visible()
        compose = page.get_by_role("button", name="Собрать видео из фотографий", exact=True)
        expect(compose).to_be_disabled()

        page.locator('input[aria-label="Изображения Stage 8"]').set_input_files(
            [str(self.red_image), str(self.blue_image)]
        )
        expect(page.get_by_text("1. red.png", exact=True)).to_be_visible(timeout=60_000)
        expect(page.get_by_text("2. blue.png", exact=True)).to_be_visible(timeout=60_000)
        page.locator('input[aria-label="Аудио Stage 8"]').set_input_files(str(self.audio))
        photo_audio = page.get_by_label("Аудио для фото-видео")
        expect(photo_audio).to_be_visible(timeout=60_000)
        _select_option_containing(photo_audio, self.audio.name)
        expect(compose).to_be_enabled()
        compose.click()
        expect(page.get_by_role("link", name="Открыть готовый рендер", exact=True)).to_be_visible(
            timeout=120_000
        )

        # Start a second task from the normal root path so prerequisite guidance
        # is observed from a truly empty project rather than an API-seeded state.
        self._create_from_visible_catalog(
            page,
            recipe_title="Аудиовизуализатор",
            project_title="Class C — аудиовизуализатор",
        )
        expect(page.get_by_role("heading", name="Аудио → визуализатор", exact=True)).to_be_visible()
        guidance = page.get_by_text("Загрузите master-аудио для визуализатора.", exact=True).first
        expect(guidance).to_be_visible()
        render = page.get_by_role("button", name="Собрать аудиовизуализатор", exact=True)
        expect(render).to_be_disabled()

        page.locator('input[aria-label="Аудио Stage 8"]').set_input_files(str(self.audio))
        master_audio = page.get_by_label("Master-аудио визуализатора")
        expect(master_audio).to_be_visible(timeout=60_000)
        _select_option_containing(master_audio, self.audio.name)
        expect(render).to_be_enabled()
        render.click()
        expect(
            page.get_by_text(
                "Аудиовизуализатор собран через Product Orchestrator и локальный FFmpeg capability.",
                exact=True,
            )
        ).to_be_visible(timeout=120_000)
        expect(page.get_by_role("link", name="Открыть готовый рендер", exact=True)).to_be_visible(
            timeout=120_000
        )

        report = {
            "entry_path": "/ -> /projects",
            "project_creation": "visible_catalog_only",
            "hidden_setup": False,
            "direct_store_fixture": False,
            "outcomes": ["photo_to_video_rendered", "visualizer_rendered"],
            "prerequisite_guidance": "visualizer_master_audio_visible_before_upload",
            "unsupported_recipe_discovery": "preserved_only_recipes_hidden",
            "optional_runtime_interpretation": (
                "local FFmpeg-backed representative outcomes succeeded; provider/runtime-specific "
                "journeys are not claimed by this evidence"
            ),
        }
        (self.artifact_dir / "class-c-cold-start.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        page.screenshot(path=str(self.artifact_dir / "class-c-cold-start-final.png"), full_page=True)


if __name__ == "__main__":
    import unittest

    unittest.main()
