"""Class C cold-start browser evidence for the intent-first product journey.

This suite deliberately avoids direct Project Store access, hidden workflow seeding
and semantic API setup. A clean user describes a desired result, creates one
project, adds a visible material and reaches a real local render through Studio.
"""

from __future__ import annotations

import json

from playwright.sync_api import expect

import test_stage8_outcomes as stage8


class ClassCColdStartBrowserOutcome(stage8.Stage8BrowserOutcomes):
    # Reuse only the clean application/media fixture bootstrap. Historical Stage 8
    # scenario coverage remains in its own module and is not inherited here.
    test_photo_and_visualizer_user_paths = None

    def test_clean_user_starts_from_intent_and_reaches_local_result(self) -> None:
        page = self._new_page()
        goal = "Сделать короткий ролик о двух цветовых состояниях"
        title = "Class C — проект от замысла"

        page.goto("/")
        page.wait_for_url("**/projects")
        expect(page.get_by_role("heading", name="Проекты", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Что хотите создать?", exact=True)).to_be_visible()

        # Clean-state discovery must not ask the user to choose technical recipes.
        expect(page.get_by_text("1. Что хотите получить?", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Фото в видео", exact=False)).to_have_count(0)
        expect(page.get_by_role("button", name="Аудиовизуализатор", exact=False)).to_have_count(0)

        page.get_by_label("Что хотите создать?").fill(goal)
        page.get_by_label("Название проекта").fill(title)
        create_button = page.get_by_role("button", name="Начать проект", exact=True)
        expect(create_button).to_be_enabled()
        create_button.click()

        page.wait_for_url("**/projects/*/studio")
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(page.get_by_text("Единый проект", exact=True)).to_be_visible()
        expect(page.get_by_text("Следующий шаг", exact=True)).to_be_visible()
        expect(page.get_by_text(goal, exact=True).first).to_be_visible()
        expect(page.get_by_text("Stage 8", exact=False)).to_have_count(0)
        expect(page.get_by_text("Product Orchestrator", exact=False)).to_have_count(0)

        page.get_by_label("Сценарий и план").fill("Красный кадр, затем завершение.")
        page.get_by_label("Добавить изображение").set_input_files(str(self.red_image))
        expect(page.get_by_label(f"Использовать {self.red_image.name}")).to_be_checked(timeout=60_000)

        page.get_by_role("button", name="Сохранить подготовку", exact=True).click()
        expect(
            page.get_by_text(
                "Замысел, план и выбранные материалы сохранены как одно состояние проекта.",
                exact=True,
            )
        ).to_be_visible(timeout=60_000)

        render = page.get_by_role("button", name="Собрать ролик", exact=True)
        expect(render).to_be_enabled(timeout=60_000)
        render.click()
        expect(
            page.get_by_text("Текущий ролик соответствует сохранённым материалам", exact=True)
        ).to_be_visible(timeout=120_000)
        expect(page.get_by_role("link", name="Открыть готовый ролик", exact=False)).to_be_visible()

        report = {
            "entry_path": "/ -> /projects -> /projects/{id}/studio",
            "project_creation": "intent_first_visible_goal",
            "recipe_selection_exposed": False,
            "hidden_setup": False,
            "direct_store_fixture": False,
            "outcomes": ["intent_saved", "own_visual_selected", "local_video_rendered"],
            "provider_claim": "no hidden generation/provider execution claimed",
        }
        (self.artifact_dir / "class-c-cold-start.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        page.screenshot(path=str(self.artifact_dir / "class-c-cold-start-final.png"), full_page=True)


if __name__ == "__main__":
    import unittest

    unittest.main()
