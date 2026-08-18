"""Product-surface browser outcomes for the Stage 9 workspace UX.

The heavy real-media fixtures and semantic assertions stay in the permanent
BrowserUserOutcomes harness. This subclass changes only the user navigation and
copy-level affordances so the same backend outcomes are exercised through the
product workspace rather than the former module-stack UI.
"""

from __future__ import annotations

import urllib.parse

from playwright.sync_api import Page, expect

import test_user_outcomes as harness


class ProductBrowserUserOutcomes(harness.BrowserUserOutcomes):
    def _create_project(self, page: Page) -> str:
        page.goto("/projects")
        expect(page.get_by_role("heading", name="Проекты", exact=True)).to_be_visible()
        title = "E2E продуктовый проект"
        page.get_by_placeholder("Название нового проекта").fill(title)
        page.get_by_role("button", name="Создать проект", exact=True).click()
        page.wait_for_url("**/projects/*")
        project_id = urllib.parse.unquote(urllib.parse.urlsplit(page.url).path.rsplit("/", 1)[-1])
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(page.get_by_test_id("workspace-edit")).to_be_visible()
        return project_id

    def _complete_targeted_edit(self, page: Page) -> None:
        self._select_original_source(page)
        self._select_range(page)
        page.locator("#uv-change-request").fill(
            "Заменить выбранные две секунды подготовленным клипом, не изменяя материал за границами диапазона."
        )
        page.get_by_role("button", name="Подготовить изменение", exact=True).click()
        expect(page.get_by_text("Последняя задача подготовлена", exact=True)).to_be_visible(timeout=30_000)

        page.get_by_role("button", name="Использовать готовый клип", exact=True).click()
        page.get_by_role("button", name="Создать предпросмотр", exact=True).click()

        result_selects = page.locator('select[aria-label^="Результат "]')
        expect(result_selects.first).to_be_visible(timeout=45_000)
        count = result_selects.count()
        self.assertGreater(count, 0, "replacement review must expose at least one visible criterion")
        for index in range(count):
            outcome = result_selects.nth(index)
            outcome.select_option("pass")
            target_card = outcome.locator(
                "xpath=ancestor::div[contains(@class,'rounded-xl')][1]"
            )
            target_card.locator("textarea").fill(
                "Browser E2E подтверждает критерий по показанному предпросмотру."
            )

        page.get_by_role("button", name="Одобрить", exact=True).click()
        expect(page.get_by_text("Проверка:", exact=False).filter(has_text="одобрено")).to_be_visible()
        page.get_by_role("button", name="Применить изменение", exact=True).click()
        expect(page.get_by_text("Изменение применено и отмечено на таймлайне.", exact=True)).to_be_visible()

        page.get_by_test_id("workspace-export").click()
        render_section = page.get_by_text(
            "Собрать принятые правки в один мастер", exact=True
        ).locator("xpath=ancestor::section[1]")
        render_section.get_by_role("button", name="Собрать мастер", exact=True).click()
        expect(
            render_section.get_by_text(
                "Мастер соответствует текущему Accepted state", exact=True
            )
        ).to_be_visible(timeout=90_000)

    def _complete_dubbing(self, page: Page, project_id: str) -> None:
        page.get_by_test_id("workspace-dubbing").click()
        expect(page.get_by_role("heading", name="Дубляж", exact=True)).to_be_visible()
        super()._complete_dubbing(page, project_id)

    def _complete_sequence_continuity(self, page: Page, project_id: str) -> None:
        page.get_by_test_id("workspace-continuity").click()
        expect(page.get_by_role("heading", name="Связность сцен", exact=True)).to_be_visible()
        super()._complete_sequence_continuity(page, project_id)
