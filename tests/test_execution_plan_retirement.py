from __future__ import annotations

import unittest
from pathlib import Path

import uv_studio.recipes as recipes
from uv_studio.api.recipes import get_recipe_registry
from uv_studio.server import app

ROOT = Path(__file__).resolve().parents[1]


class ExecutionPlanRetirementTests(unittest.TestCase):
    def test_recipe_execution_projection_files_are_retired(self) -> None:
        self.assertFalse((ROOT / "uv_studio" / "api" / "execution.py").exists())
        self.assertFalse((ROOT / "uv_studio" / "recipes" / "execution.py").exists())
        self.assertFalse(hasattr(recipes, "resolve_project_execution"))
        self.assertFalse(hasattr(recipes, "RecipeExecutionPlan"))

    def test_frontend_execution_plan_client_is_retired(self) -> None:
        source = (ROOT / "frontend" / "lib" / "projectsApi.ts").read_text(encoding="utf-8")
        self.assertNotIn("getProjectExecutionPlan", source)
        self.assertNotIn("ProjectExecutionPlan", source)
        self.assertNotIn("/execution-plan", source)

    def test_execution_plan_route_is_not_mounted(self) -> None:
        paths = {route.path for route in app.routes}
        self.assertNotIn("/api/uv/projects/{project_id}/execution-plan", paths)

    def test_remaining_recipe_registry_and_product_workflow_are_preserved(self) -> None:
        registry = get_recipe_registry()
        self.assertEqual(registry.get("general_video").recipe_id, "general_video")
        paths = {route.path for route in app.routes}
        self.assertIn("/api/uv/projects/{project_id}/workflow", paths)
        self.assertIn("/api/uv/projects/studio/directions", paths)
        self.assertIn("/api/uv/projects/studio", paths)


if __name__ == "__main__":
    unittest.main()
