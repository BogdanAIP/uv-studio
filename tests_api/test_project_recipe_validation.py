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

    def test_known_specialized_recipe_can_create_project(self) -> None:
        response = self.client.post(
            "/api/uv/projects",
            json={"title": "Motion Transfer", "recipe_id": "action_transfer"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["recipe_id"], "action_transfer")

    def test_unknown_recipe_is_rejected_on_create(self) -> None:
        response = self.client.post(
            "/api/uv/projects",
            json={"title": "Unknown", "recipe_id": "unknown_recipe"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("Unknown recipe_id", response.json()["detail"])
        self.assertEqual(self.store.list_projects(), [])

    def test_unknown_recipe_is_rejected_on_update_without_mutating_project(self) -> None:
        created = self.client.post(
            "/api/uv/projects",
            json={"title": "Known", "recipe_id": "general_video"},
        ).json()
        project_id = created["project_id"]

        response = self.client.patch(
            f"/api/uv/projects/{project_id}",
            json={"recipe_id": "unknown_recipe"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.store.load_project(project_id).recipe_id, "general_video")

    def test_known_recipe_change_is_persisted(self) -> None:
        created = self.client.post(
            "/api/uv/projects",
            json={"title": "Known", "recipe_id": "general_video"},
        ).json()
        project_id = created["project_id"]

        response = self.client.patch(
            f"/api/uv/projects/{project_id}",
            json={"recipe_id": "narrated_video"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["recipe_id"], "narrated_video")
        self.assertEqual(self.store.load_project(project_id).recipe_id, "narrated_video")


if __name__ == "__main__":
    unittest.main()
