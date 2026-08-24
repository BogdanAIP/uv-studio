"""Product-owned replacements for the retired cross-workspace browser regression.

The historical Stage 4C/5/6 browser test mounted Dubbing and Sequence Continuity
inside an `action_transfer` project through the old generic frontend fallback.
Product Truth reconciliation intentionally removes that leakage. These tests
preserve the valuable routing/isolation coverage while keeping advanced tools out
of product workspaces that do not currently own a user-facing path for them.
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


class ProductOwnedStoryIsolationBrowserOutcome(legacy.BrowserUserOutcomes):
    # Story is currently preparation-only. The primary Story route must not
    # re-expose the old Stage 6 continuity UI just to preserve a historical
    # browser regression; advanced continuity needs its own product-owned route
    # before it can be advertised again.
    test_targeted_edit_isolated_while_dubbing_and_sequence_regressions_remain_operable = None

    def test_story_primary_route_is_preparation_only_without_foreign_panels(self) -> None:
        page = self._new_page()
        try:
            project_id = self._create_project_via_api(
                page,
                title="E2E Product-owned Story Isolation",
                recipe_id="story_video",
            )
            expect(
                page.get_by_role(
                    "heading",
                    name="Сейчас это подготовка истории, а не генератор готового фильма",
                    exact=True,
                )
            ).to_be_visible()
            expect(page.get_by_role("heading", name="Подготовка сюжетного видео", exact=True)).to_be_visible()

            # The guided Story surface must not leak unrelated or not-yet-routed
            # advanced workspaces into the first-run journey.
            expect(page.get_by_text("Непрерывность связанных кадров", exact=True)).to_have_count(0)
            expect(page.get_by_text("Дубляж в том же проекте и таймлайне", exact=True)).to_have_count(0)
            expect(
                page.get_by_role("heading", name="Точечное редактирование исходного видео", exact=True)
            ).to_have_count(0)
            expect(page.get_by_text("Stage 6", exact=False)).to_have_count(0)
            expect(page.get_by_text("Stage 8", exact=False)).to_have_count(0)

            report = {
                "project_id": project_id,
                "story_route": "preparation_only",
                "advanced_continuity_visible": False,
                "foreign_workspace_leakage": False,
                "frontend": legacy.FRONTEND_ORIGIN,
            }
            (self.artifact_dir / "story-product-owned-isolation.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            page.screenshot(
                path=str(self.artifact_dir / "story-product-owned-isolation.png"),
                full_page=True,
            )
        except Exception:
            page.screenshot(
                path=str(self.artifact_dir / "story-product-owned-isolation-failure.png"),
                full_page=True,
            )
            raise
