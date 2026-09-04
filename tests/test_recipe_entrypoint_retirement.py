from __future__ import annotations

import unittest
from pathlib import Path

from pydantic import ValidationError

from uv_studio.api.execution import get_recipe_registry
from uv_studio.api.projects import UpdateProjectRequest

ROOT = Path(__file__).resolve().parents[1]


class RecipeEntrypointRetirementTests(unittest.TestCase):
    def test_retired_frontend_recipe_clients_are_absent(self) -> None:
        self.assertFalse((ROOT / "frontend/lib/recipesApi.ts").exists())
        projects_api = (ROOT / "frontend/lib/projectsApi.ts").read_text(encoding="utf-8")
        self.assertNotIn("createUV" + "Project", projects_api)
        self.assertNotIn("Create" + "ProjectInput", projects_api)

    def test_retired_backend_recipe_entrypoints_are_absent(self) -> None:
        self.assertFalse((ROOT / "uv_studio/api/recipes.py").exists())

        server = (ROOT / "uv_studio/server.py").read_text(encoding="utf-8")
        self.assertNotIn("recipes_router", server)
        self.assertNotIn("uv_studio.api.recipes", server)

        projects_api = (ROOT / "uv_studio/api/projects.py").read_text(encoding="utf-8")
        self.assertNotIn("class Create" + "ProjectRequest", projects_api)
        self.assertNotIn('@router.post("",', projects_api)
        self.assertNotIn("uv_studio.api.recipes", projects_api)

    def test_recipe_identity_is_not_a_generic_project_patch_field(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateProjectRequest.model_validate({"recipe_id": "general_video"})

    def test_execution_plan_retains_internal_recipe_registry_until_later_slice(self) -> None:
        registry = get_recipe_registry()
        self.assertEqual(registry.get("general_video").recipe_id, "general_video")


if __name__ == "__main__":
    unittest.main()
