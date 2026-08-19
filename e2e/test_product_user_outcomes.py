"""Permanent browser outcomes through the Stage 9 product workspace.

The heavy real-media fixtures and semantic API assertions stay in the original
BrowserUserOutcomes harness. This subclass changes only the visible product
navigation and controls so the same durable outcomes are proved without relying
on implementation vocabulary.
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
            target_card = outcome.locator("xpath=ancestor::div[contains(@class,'rounded-xl')][1]")
            target_card.locator("textarea").fill(
                "Browser E2E подтверждает критерий по показанному предпросмотру."
            )

        page.get_by_role("button", name="Одобрить", exact=True).click()
        expect(page.get_by_text("Проверка:", exact=False).filter(has_text="одобрено")).to_be_visible()
        page.get_by_role("button", name="Применить изменение", exact=True).click()
        expect(page.get_by_text("Изменение применено и отмечено на таймлайне.", exact=True)).to_be_visible()

        page.get_by_test_id("workspace-export").click()
        render_section = page.get_by_text("Собрать применённые изменения", exact=True).locator("xpath=ancestor::section[1]")
        render_section.get_by_role("button", name="Собрать итоговое видео", exact=True).click()
        expect(render_section.get_by_text("Итоговое видео актуально", exact=True)).to_be_visible(timeout=90_000)

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
        harness._select_option_containing(source_select, self.source_video.name)

        translation_card = dubbing.get_by_text("Текст и перевод", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        expect(translation_card.get_by_text("hello world", exact=True)).to_be_visible()
        translation_card.get_by_label("Перевод segment_1", exact=True).fill("привет мир")
        translation_card.get_by_role("button", name="Сохранить перевод", exact=True).click()
        expect(dubbing.get_by_text("Перевод сохранён.", exact=True)).to_be_visible()

        audio_card = dubbing.get_by_text("Речевая дорожка", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        audio_card.locator('input[type="file"][accept="audio/*"]').set_input_files(str(self.prepared_speech))
        audio_select = audio_card.get_by_label("Речевая дорожка", exact=True)
        expect(audio_select.locator("option:checked")).to_have_text(self.prepared_speech.name, timeout=30_000)
        audio_card.get_by_role("button", name="Привязать дорожку к тексту", exact=True).click()
        expect(dubbing.get_by_text("Речевая дорожка привязана к выбранному тексту.", exact=True)).to_be_visible()

        review_card = dubbing.get_by_text("Проверка и применение", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        review_card.get_by_label("Содержание и произношение проверены", exact=True).check()
        review_card.get_by_label("Синхронизация с видео проверена", exact=True).check()
        review_card.get_by_role("button", name="Одобрить", exact=True).click()
        expect(review_card.get_by_text("Проверка пройдена", exact=True)).to_be_visible(timeout=45_000)
        expect(review_card.get_by_text("Синхронизация: норма", exact=False)).to_be_visible()
        review_card.get_by_role("button", name="Применить озвучку", exact=True).click()
        expect(dubbing.get_by_text("Озвучка применена.", exact=True)).to_be_visible()

        result = dubbing.get_by_text("Видео с применённой озвучкой", exact=True).locator(
            "xpath=ancestor::div[contains(@class,'rounded-2xl')][1]"
        )
        result.get_by_role("button", name="Собрать видео", exact=True).click()
        expect(result.get_by_text("Видео готово", exact=True)).to_be_visible(timeout=90_000)

    def _complete_sequence_continuity(self, page: Page, project_id: str) -> None:
        page.get_by_test_id("workspace-continuity").click()
        expect(page.get_by_role("heading", name="Связность сцен", exact=True).first).to_be_visible()

        page.get_by_role("button", name="Включить", exact=True).click()
        sequence = page.get_by_text(
            "Следующий вариант сравнивается с последним принятым опорным кадром", exact=False
        ).locator("xpath=ancestor::section[1]")
        expect(sequence).to_be_visible(timeout=30_000)

        sequence.get_by_label("Замысел связанного кадра", exact=True).fill(
            "Зафиксировать первый опорный кадр для следующей сцены."
        )
        sequence.get_by_label("Фиксированное условие непрерывности", exact=True).fill(
            "Сохранить идентичность субъекта и направление движения вправо."
        )
        sequence.get_by_role("button", name="Сохранить кадр", exact=True).click()

        video_select = sequence.get_by_label("Видео для подготовленного дубля", exact=True)
        harness._select_option_containing(video_select, self.source_video.name)
        sequence.get_by_role("button", name="Проверить этот вариант", exact=True).click()
        sequence.get_by_role("button", name="Сравнить границу", exact=True).click()
        expect(sequence.get_by_text("Это первый кадр последовательности — предыдущая опора не требуется.", exact=True)).to_be_visible(timeout=30_000)
        expect(sequence.get_by_text("Новый вариант", exact=True)).to_be_visible()

        sequence.get_by_label("Результат критерия 1", exact=True).select_option("pass")
        sequence.get_by_label("Наблюдение по связанному кадру", exact=True).fill("Subject exits screen-right.")
        sequence.get_by_label("Решение по связанному кадру", exact=True).select_option("approved")
        sequence.get_by_role("button", name="Сохранить проверку", exact=True).click()
        first_apply = sequence.get_by_role("button", name="Применить вариант", exact=True)
        expect(first_apply).to_be_enabled(timeout=30_000)
        first_apply.click()
        expect(sequence.get_by_text("Вариант применён. Он может стать опорой", exact=False)).to_be_visible(timeout=30_000)

        state_after_accept = harness._api_json("GET", harness._project_path(project_id, "/sequence/state"))
        first_sequence = state_after_accept["sequences"][0]
        first_take = next(take for take in first_sequence["takes"] if take["shot_id"] == "shot_01" and take["status"] == "accepted")
        first_anchor_id = first_take["take_id"]
        first_anchor = sequence.get_by_role("button", name="Сделать опорой", exact=True)
        expect(first_anchor).to_be_enabled(timeout=30_000)
        first_anchor.click()
        expect(sequence.get_by_text("Опорный кадр обновлён.", exact=True)).to_be_visible(timeout=30_000)

        state_after_anchor = harness._api_json("GET", harness._project_path(project_id, "/sequence/state"))
        self.assertEqual(state_after_anchor["sequences"][0]["anchor_take_id"], first_anchor_id)

        sequence.get_by_label("Замысел связанного кадра", exact=True).fill(
            "Продолжить принятый выход вправо в более крупном втором кадре."
        )
        sequence.get_by_label("Фиксированное условие непрерывности", exact=True).fill(
            "Продолжить направление движения принятой опоры вправо."
        )
        sequence.get_by_label("Разрешённое изменение непрерывности", exact=True).fill(
            "Разрешить более крупное кадрирование."
        )
        sequence.get_by_role("button", name="Сохранить кадр", exact=True).click()

        harness._select_option_containing(video_select, self.replacement_video.name)
        sequence.get_by_role("button", name="Проверить этот вариант", exact=True).click()
        sequence.get_by_role("button", name="Сравнить границу", exact=True).click()
        expect(sequence.get_by_text("Принятый опорный кадр", exact=True)).to_be_visible(timeout=30_000)
        expect(sequence.get_by_text("Новый вариант", exact=True)).to_be_visible()
        expect(sequence.locator("video")).to_have_count(2)

        current_state = harness._api_json("GET", harness._project_path(project_id, "/sequence/state"))
        current_sequence = current_state["sequences"][0]
        prepared_take = next(take for take in current_sequence["takes"] if take["shot_id"] == "shot_02" and take["status"] == "prepared")
        observed_context = harness._api_json(
            "GET",
            harness._project_path(
                project_id,
                f"/sequence/{urllib.parse.quote(current_sequence['sequence_id'], safe='')}/takes/{urllib.parse.quote(prepared_take['take_id'], safe='')}/context?window_us=1000000&samples=3",
            ),
        )
        self.assertEqual(observed_context["anchor"]["take_id"], first_anchor_id)
        self.assertEqual(observed_context["anchor"]["observations"][0]["statement"], "Subject exits screen-right.")
        self.assertEqual(len(observed_context["anchor"]["sample_times_us"]), 3)
        self.assertEqual(len(observed_context["candidate"]["sample_times_us"]), 3)

        sequence.get_by_label("Результат критерия 1", exact=True).select_option("pass")
        sequence.get_by_label("Наблюдение по связанному кадру", exact=True).fill(
            "Candidate continues the accepted screen-right direction."
        )
        sequence.get_by_label("Решение по связанному кадру", exact=True).select_option("approved")
        sequence.get_by_role("button", name="Сохранить проверку", exact=True).click()
        second_apply = sequence.get_by_role("button", name="Применить вариант", exact=True)
        expect(second_apply).to_be_enabled(timeout=30_000)
        second_apply.click()

        final_pre_anchor = harness._api_json("GET", harness._project_path(project_id, "/sequence/state"))["sequences"][0]
        second_take = next(take for take in final_pre_anchor["takes"] if take["shot_id"] == "shot_02" and take["status"] == "accepted")
        second_anchor_id = second_take["take_id"]
        second_anchor = sequence.get_by_role("button", name="Сделать опорой", exact=True)
        expect(second_anchor).to_be_enabled(timeout=30_000)
        second_anchor.click()
        expect(sequence.get_by_text("Опорный кадр обновлён.", exact=True)).to_be_visible(timeout=30_000)

        final_state = harness._api_json("GET", harness._project_path(project_id, "/sequence/state"))["sequences"][0]
        accepted = [take for take in final_state["takes"] if take["status"] == "accepted"]
        self.assertEqual(len(accepted), 2)
        self.assertEqual(final_state["anchor_take_id"], second_anchor_id)
        self.assertNotEqual(final_state["anchor_take_id"], first_anchor_id)
