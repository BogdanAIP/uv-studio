"""Class C cold-start browser evidence for the Studio production-direction path.

This suite deliberately avoids direct Project Store access, hidden workflow seeding,
legacy recipe selection and semantic API setup. The user chooses a product-level
Production Direction, then creates, populates, edits, reopens and exports through the
same visible Studio controls available to a clean user state.
"""

from __future__ import annotations

import json

from playwright.sync_api import expect

import test_stage8_outcomes as stage8


class ClassCColdStartBrowserOutcome(stage8.Stage8BrowserOutcomes):
    # Reuse only the clean application/media fixture bootstrap. The historical
    # Stage 8 browser scenario remains covered by its own compatibility module
    # and must not be inherited as Class C product truth.
    test_photo_and_visualizer_user_paths = None

    def test_clean_user_chooses_direction_reopens_and_exports_studio_project(self) -> None:
        page = self._new_page()
        project_title = "Class C — Studio timeline"

        page.goto("/")
        page.wait_for_url("**/projects")
        expect(page.get_by_role("heading", name="Проекты", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Что хотите создать?", exact=True)).to_be_visible()

        # Product directions are first-class setup choices over one Studio Core.
        for direction_title in (
            "Микродрама / сюжетное видео",
            "Реклама / продукт",
            "Музыкальный клип",
            "Видео с диктором",
            "Киноозвучка / Кинобатл",
            "Свободный проект",
        ):
            expect(page.get_by_role("button", name=direction_title, exact=False)).to_be_visible()

        # Operation-level tools do not return as top-level project identities.
        for tool_title in (
            "Фото в видео",
            "Аудиовизуализатор",
            "Перенос движения",
            "Говорящий персонаж",
            "Performance / lip-sync",
            "Дубляж видео",
        ):
            expect(page.get_by_role("button", name=tool_title, exact=False)).to_have_count(0)

        free_project = page.get_by_role("button", name="Свободный проект", exact=False)
        free_project.click()
        expect(free_project).to_have_attribute("aria-pressed", "true")

        title_input = page.get_by_placeholder("Название проекта")
        title_input.fill(project_title)
        create_button = page.get_by_role("button", name="Создать и открыть Studio", exact=True)
        expect(create_button).to_be_enabled()
        create_button.click()

        page.wait_for_url("**/projects/*/studio", timeout=30_000)
        expect(page.get_by_role("heading", name=project_title, exact=True)).to_be_visible()
        expect(page.get_by_text("Media Bin", exact=True)).to_be_visible()
        expect(page.get_by_text("Inspector", exact=True)).to_be_visible()
        expect(page.get_by_text("Timeline", exact=True)).to_be_visible()
        expect(page.get_by_text("AI Tools", exact=True)).to_be_visible()
        expect(page.get_by_text("Product Orchestrator", exact=True)).to_have_count(0)
        expect(page.get_by_text("Stage 8", exact=False)).to_have_count(0)

        page.get_by_label("Импортировать медиа в Studio").set_input_files(str(self.red_image))
        expect(page.get_by_text(self.red_image.name, exact=True).first).to_be_visible(timeout=60_000)

        page.get_by_role("button", name="Video track", exact=False).click()
        add_button = page.get_by_role("button", name="Добавить в конец дорожки", exact=True)
        expect(add_button).to_be_visible(timeout=30_000)
        expect(add_button).to_be_enabled()
        add_button.click()

        clip = page.get_by_role("button", name=f"Клип {self.red_image.name}", exact=True)
        expect(clip).to_be_visible(timeout=30_000)
        clip.click()
        expect(page.get_by_text("Клип на timeline", exact=True)).to_be_visible()

        # Exercise a real shared timeline mutation through Inspector.
        duration = page.get_by_label("Длительность клипа")
        duration.fill("2")
        page.get_by_role("button", name="Применить trim", exact=True).click()
        expect(page.get_by_text("00:02.00 · 1 tracks", exact=True)).to_be_visible(timeout=30_000)

        # Reopen through the normal projects page. Direction identity and canonical
        # timeline state must survive browser navigation and server reload.
        page.get_by_role("link", name="← Проекты", exact=True).click()
        page.wait_for_url("**/projects")
        expect(page.get_by_role("heading", name=project_title, exact=True)).to_be_visible()
        expect(page.get_by_text("Свободный проект", exact=True).last).to_be_visible()
        page.get_by_role("link", name="Открыть Studio", exact=False).first.click()
        page.wait_for_url("**/projects/*/studio")
        expect(page.get_by_role("button", name=f"Клип {self.red_image.name}", exact=True)).to_be_visible(
            timeout=30_000
        )
        expect(page.get_by_text("00:02.00 · 1 tracks", exact=True)).to_be_visible()

        export_button = page.get_by_role("button", name="Экспортировать", exact=True)
        expect(export_button).to_be_enabled()
        export_button.click()
        expect(page.get_by_role("link", name="Открыть экспорт", exact=True)).to_be_visible(
            timeout=120_000
        )

        report = {
            "entry_path": "/ -> /projects -> choose Production Direction -> /projects/{id}/studio",
            "project_creation": "production_direction_visible_controls_only",
            "production_direction": "free_project",
            "legacy_recipe_selection": False,
            "hidden_setup": False,
            "direct_store_fixture": False,
            "media_import": self.red_image.name,
            "timeline_mutations": ["create_track", "add_clip", "trim_clip"],
            "reopen_persistence": True,
            "outcomes": [
                "production_direction_persisted",
                "canonical_timeline_persisted",
                "studio_export_rendered",
            ],
            "compatibility_ui": "legacy recipe workflows are not the clean creation path",
            "optional_runtime_interpretation": (
                "local FFmpeg-backed Studio export succeeded; AI/provider generation is not claimed"
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
