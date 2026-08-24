from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.application.creative_projects import (
    CREATIVE_EXTENSION_KEY,
    CreativeProjectError,
    CreativeProjectService,
)
from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
    build_builtin_capability_registry,
)
from uv_studio.projects.store import ProjectStore
from uv_studio.recipes import build_builtin_registry


class CreativeProjectServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.registry = build_builtin_capability_registry()
        self.recipes = build_builtin_registry()
        self.service = CreativeProjectService(self.store, self.registry, self.recipes)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _route(plan: dict, phase_id: str, route_id: str) -> dict:
        phase = next(item for item in plan["phases"] if item["phase_id"] == phase_id)
        return next(item for item in phase["routes"] if item["route_id"] == route_id)

    def test_goal_only_creation_uses_internal_recipe_but_stores_user_intent(self) -> None:
        project = self.service.create(goal="Сделай короткий ролик о ночном городе")

        self.assertEqual(project.recipe_id, "general_video")
        self.assertEqual(project.title, "Сделай короткий ролик о ночном городе")
        creative = project.extensions[CREATIVE_EXTENSION_KEY]
        self.assertEqual(creative["goal"], "Сделай короткий ролик о ночном городе")
        self.assertEqual(creative["script"], "")
        self.assertEqual(creative["material_source_ids"], [])
        self.assertEqual(creative["provider_policy"], "local_free_first")
        self.assertFalse(creative["allow_paid_remote"])

        plan = self.service.plan(project.project_id)
        self.assertEqual(plan["goal"], creative["goal"])
        self.assertEqual(plan["material_source_ids"], [])
        self.assertEqual(
            [phase["phase_id"] for phase in plan["phases"]],
            ["intent", "plan", "visuals", "audio", "assembly", "review"],
        )
        self.assertEqual(plan["overall_state"], "needs_materials")

    def test_builtin_videoclaw_generation_is_not_presented_as_configurable_execution(self) -> None:
        project = self.service.create(goal="Сделай ролик с нуля")
        plan = self.service.plan(project.project_id)

        for phase_id, route_id in (
            ("plan", "generate_text"),
            ("visuals", "generate_images"),
            ("visuals", "generate_video"),
        ):
            route = self._route(plan, phase_id, route_id)
            self.assertEqual(route["state"], "unavailable")
            self.assertEqual(route["configuration_required_count"], 0)

        own_media = self._route(plan, "visuals", "use_own_media")
        self.assertEqual(own_media["state"], "ready")
        self.assertEqual(own_media["route_class"], "local_input")

    def test_real_mcp_offer_changes_plan_without_provider_specific_product_code(self) -> None:
        self.registry.register_adapter(
            AdapterDefinition(
                "mcp.test_provider",
                "Test MCP provider",
                "test external generator",
                AdapterKind.MCP,
            )
        )
        self.registry.register_offer(
            CapabilityOffer(
                "mcp.test_provider.image_generate",
                "image.generate",
                "mcp.test_provider",
                "Test image generator",
                OfferAvailability.AVAILABLE,
                "ready through discovered MCP binding",
                LocalityClass.REMOTE,
                CostClass.POTENTIALLY_PAID,
                True,
            )
        )
        project = self.service.create(goal="Сделай ролик с иллюстрациями")

        route = self._route(self.service.plan(project.project_id), "visuals", "generate_images")
        self.assertEqual(route["state"], "ready")
        self.assertEqual(route["route_class"], "external_paid")
        self.assertTrue(route["has_external"])
        self.assertTrue(route["may_cost_money"])
        self.assertEqual(route["available_offer_count"], 1)

    def test_script_update_is_canonical_project_state(self) -> None:
        project = self.service.create(goal="Ролик о лаборатории", title="Лаборатория")
        updated = self.service.update_intent(
            project.project_id,
            script="1. Общий план.\n2. Установка.\n3. Результат.",
        )

        self.assertEqual(updated.title, "Лаборатория")
        self.assertIn("Установка", updated.extensions[CREATIVE_EXTENSION_KEY]["script"])
        plan = self.service.plan(project.project_id)
        self.assertIn("Установка", plan["script"])
        phase = next(item for item in plan["phases"] if item["phase_id"] == "plan")
        self.assertEqual(phase["state"], "complete")

    def test_non_creative_project_is_rejected_by_creative_plan(self) -> None:
        project = self.store.create_project(title="Old project", recipe_id="general_video")
        with self.assertRaises(CreativeProjectError):
            self.service.plan(project.project_id)


if __name__ == "__main__":
    unittest.main()
