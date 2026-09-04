from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class RecipeCreationCatalogApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.temp.name))
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        self.temp.cleanup()

    def _create_modern_project(self) -> dict[str, object]:
        response = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Modern", "direction_id": "free_project"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_recipe_catalog_is_no_longer_a_public_creation_surface(self) -> None:
        self.assertEqual(self.client.get("/api/uv/recipes").status_code, 404)
        self.assertEqual(self.client.get("/api/uv/recipes/action_transfer").status_code, 404)

    def test_direct_recipe_project_creation_is_retired_for_all_recipe_ids(self) -> None:
        for recipe_id in ("general_video", "action_transfer", "unknown_recipe"):
            response = self.client.post(
                "/api/uv/projects",
                json={"title": "Unsupported", "recipe_id": recipe_id},
            )
            self.assertEqual(response.status_code, 405, response.text)
        self.assertEqual(self.store.list_projects(), [])

    def test_recipe_switch_is_rejected_as_unknown_project_patch_field(self) -> None:
        created = self._create_modern_project()
        project_id = created["project_id"]
        original_recipe_id = self.store.load_project(project_id).recipe_id

        response = self.client.patch(
            f"/api/uv/projects/{project_id}",
            json={"recipe_id": "general_video"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.store.load_project(project_id).recipe_id, original_recipe_id)


if __name__ == "__main__":
    unittest.main()
