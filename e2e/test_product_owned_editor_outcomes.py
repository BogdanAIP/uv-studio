"""Product-owned replacements for the retired cross-workspace browser regression.

The historical Stage 4C/5/6 browser test mounted Dubbing and Sequence Continuity
inside an `action_transfer` project through the old generic frontend fallback.
Product Truth reconciliation intentionally removes that leakage. These tests
preserve the valuable outcome coverage while running each workflow only in a
Product Orchestrator-owned workspace.
"""

from __future__ import annotations

import json

from playwright.sync_api import expect

import test_user_outcomes as legacy


class ProductOwnedTargetedEditBrowserOutcome(legacy.BrowserUserOutcomes):
    # Do not inherit the historical cross-workspace test; this class replaces
    # it with the product-owned Targeted Edit outcome below.
    test_targeted_edit_isolated_while_dubbing_and_sequence_regressions_remain_operable = None

    def test_targeted_edit_reaches_accepted_render_without_foreign_panels(self) -> None:
        page = self._new_page()
        try:
            project_id = self._create_project_via_api(
                page,
                title="E2E Product-owned Targeted Edit",
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

            report = {
                "project_id": project_id,
                "targeted_edit": "accepted_and_rendered",
                "routing": "targeted_edit_only",
                "frontend": legacy.FRONTEND_ORIGIN,
            }
            (self.artifact_dir / "targeted-edit-product-owned.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            page.screenshot(
                path=str(self.artifact_dir / "targeted-edit-product-owned.png"),
                full_page=True,
            )
        except Exception:
            page.screenshot(
                path=str(self.artifact_dir / "targeted-edit-product-owned-failure.png"),
                full_page=True,
            )
            raise


class ProductOwnedSequenceContinuityBrowserOutcome(legacy.BrowserUserOutcomes):
    # Do not inherit the historical cross-workspace test; this class replaces
    # it with Story-owned Sequence Continuity coverage below.
    test_targeted_edit_isolated_while_dubbing_and_sequence_regressions_remain_operable = None

    def test_story_owns_two_shot_sequence_review_accept_and_reanchor(self) -> None:
        page = self._new_page()
        try:
            project_id = self._create_project_via_api(
                page,
                title="E2E Product-owned Story Continuity",
                recipe_id="story_video",
            )
            expect(
                page.get_by_role("heading", name="Сюжетное рабочее пространство", exact=True)
            ).to_be_visible()
            expect(page.get_by_text("Непрерывность связанных кадров", exact=True)).to_be_visible()
            expect(page.get_by_text("Дубляж в том же проекте и таймлайне", exact=True)).to_have_count(0)
            expect(
                page.get_by_role("heading", name="Точечное редактирование исходного видео", exact=True)
            ).to_have_count(0)

            video_picker = page.get_by_label("Stage 8 workspace video", exact=True)
            video_picker.set_input_files(str(self.source_video))
            expect(page.get_by_text("Видео добавлено в материалы проекта.", exact=True)).to_be_visible(
                timeout=45_000
            )
            video_picker.set_input_files(str(self.replacement_video))
            expect(page.get_by_text(self.replacement_video.name, exact=True)).to_be_visible(
                timeout=45_000
            )

            self._complete_sequence_continuity(page, project_id)

            report = {
                "project_id": project_id,
                "sequence_continuity": "two_linked_takes_accepted_and_reanchored",
                "routing": "story_owned_continuity",
                "frontend": legacy.FRONTEND_ORIGIN,
            }
            (self.artifact_dir / "story-continuity-product-owned.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            page.screenshot(
                path=str(self.artifact_dir / "story-continuity-product-owned.png"),
                full_page=True,
            )
        except Exception:
            page.screenshot(
                path=str(self.artifact_dir / "story-continuity-product-owned-failure.png"),
                full_page=True,
            )
            raise
