from __future__ import annotations

import unittest
from pathlib import Path

from pydantic import ValidationError

from uv_studio.api.execution import get_recipe_registry
from uv_studio.api.projects import UpdateProjectRequest
from uv_studio.server import app

ROOT = Path(__file__).resolve().parents[1]


class RecipeEntrypointRetirementTests(unittest.TestCase):
    def test_retired_frontend_recipe_clients_are_absent(self) -> None:
        self.assertFalse((ROOT / "frontend/lib/recipesApi.ts").exists())
        projects_api = (ROOT / "frontend/lib/projectsApi.ts").read_text(encoding="utf-8")
        self.assertNotIn("createUV" + "Project", projects_api)
        self.assertNotIn("Create" + "ProjectInput", projects_api)

    def test_recipe_catalog_and_recipe_creation_are_not_mounted(self) -> None:
        methods_by_path: dict[str, set[str]] = {}
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if isinstance(path, str) and methods:
                methods_by_path.setdefault(path, set()).update(methods)

        self.assertFalse(any(path.startswith("/api/uv/recipes") for path in methods_by_path))
        self.assertNotIn("POST", methods_by_path.get("/api/uv/projects", set()))

    def test_recipe_identity_is_not_a_generic_project_patch_field(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateProjectRequest.model_validate({"recipe_id": "general_video"})

    def test_execution_plan_retains_internal_recipe_registry_until_later_slice(self) -> None:
        registry = get_recipe_registry()
        self.assertEqual(registry.get("general_video").recipe_id, "general_video")


if __name__ == "__main__":
    unittest.main()
