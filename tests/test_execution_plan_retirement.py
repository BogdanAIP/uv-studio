from __future__ import annotations

import unittest
from pathlib import Path

import uv_studio.recipes as recipes
from uv_studio.api.recipes import get_recipe_registry

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

    def test_server_no_longer_mounts_execution_plan_router(self) -> None:
        source = (ROOT / "uv_studio" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "from uv_studio.api.execution import router as execution_router",
            source,
        )
        self.assertNotIn("app.include_router(execution_router)", source)

    def test_remaining_recipe_registry_and_modern_compatibility_routers_are_preserved(self) -> None:
        registry = get_recipe_registry()
        self.assertEqual(registry.get("general_video").recipe_id, "general_video")
        source = (ROOT / "uv_studio" / "server.py").read_text(encoding="utf-8")
        self.assertIn("project_workflow_router", source)
        self.assertIn("app.include_router(project_workflow_router)", source)
        self.assertIn("studio_timeline_router", source)
        self.assertIn("app.include_router(studio_timeline_router)", source)


if __name__ == "__main__":
    unittest.main()
