from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class ProjectRecipeValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _create_modern_project(self) -> str:
        response = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Known", "direction_id": "free_project"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["project_id"]

    def test_recipe_specific_creation_validation_is_replaced_by_retired_route(self) -> None:
        for recipe_id in ("general_video", "action_transfer", "unknown_recipe"):
            response = self.client.post(
                "/api/uv/projects",
                json={"title": "Recipe Create", "recipe_id": recipe_id},
            )
            self.assertEqual(response.status_code, 405, response.text)
        self.assertEqual(self.store.list_projects(), [])

    def test_recipe_identity_cannot_be_rebound_through_generic_update(self) -> None:
        project_id = self._create_modern_project()
        original = self.store.load_project(project_id).recipe_id

        for recipe_id in ("general_video", "narrated_video", "unknown_recipe"):
            response = self.client.patch(
                f"/api/uv/projects/{project_id}",
                json={"recipe_id": recipe_id},
            )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(self.store.load_project(project_id).recipe_id, original)


if __name__ == "__main__":
    unittest.main()
