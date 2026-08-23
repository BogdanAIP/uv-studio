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

    def test_catalog_hides_recipes_without_authoritative_product_workflow(self) -> None:
        response = self.client.get("/api/uv/recipes")
        self.assertEqual(response.status_code, 200, response.text)
        ids = {item["recipe_id"] for item in response.json()}

        for recipe_id in {
            "general_video",
            "narrated_video",
            "music_video",
            "story_video",
            "commercial_product",
            "photo_to_video",
            "visualizer",
            "free_project",
        }:
            self.assertIn(recipe_id, ids)

        for recipe_id in {"action_transfer", "digital_human", "performance_lip_sync"}:
            self.assertNotIn(recipe_id, ids)

    def test_preserved_recipe_metadata_remains_addressable(self) -> None:
        for recipe_id in ("action_transfer", "digital_human", "performance_lip_sync"):
            response = self.client.get(f"/api/uv/recipes/{recipe_id}")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["recipe_id"], recipe_id)

    def test_direct_project_creation_rejects_preserved_only_recipe(self) -> None:
        response = self.client.post(
            "/api/uv/projects",
            json={"title": "Unsupported", "recipe_id": "action_transfer"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("not currently available for new project creation", response.json()["detail"])
        self.assertEqual(self.store.list_projects(), ())

    def test_recipe_switch_rejects_preserved_only_recipe(self) -> None:
        created = self.client.post(
            "/api/uv/projects",
            json={"title": "General", "recipe_id": "general_video"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        project_id = created.json()["project_id"]

        response = self.client.patch(
            f"/api/uv/projects/{project_id}",
            json={"recipe_id": "digital_human"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.store.load_project(project_id).recipe_id, "general_video")


if __name__ == "__main__":
    unittest.main()
