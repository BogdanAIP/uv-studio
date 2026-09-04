from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.project_common import get_project_store
from uv_studio.api.execution import get_recipe_registry
from uv_studio.projects.store import ProjectStore
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

    def test_recipe_identity_cannot_be_switched_through_project_patch(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            store = ProjectStore(Path(raw) / "projects")
            app.dependency_overrides[get_project_store] = lambda: store
            client = TestClient(app)
            try:
                created = client.post(
                    "/api/uv/projects/studio",
                    json={"title": "Modern", "direction_id": "free_project"},
                )
                self.assertEqual(created.status_code, 201, created.text)
                project_id = created.json()["project_id"]

                response = client.patch(
                    f"/api/uv/projects/{project_id}",
                    json={"recipe_id": "general_video"},
                )
                self.assertEqual(response.status_code, 422, response.text)
            finally:
                client.close()
                app.dependency_overrides.clear()

    def test_execution_plan_retains_internal_recipe_registry_until_later_slice(self) -> None:
        registry = get_recipe_registry()
        self.assertEqual(registry.get("general_video").recipe_id, "general_video")


if __name__ == "__main__":
    unittest.main()
