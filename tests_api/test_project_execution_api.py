from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class ProjectExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _create(self, recipe_id: str) -> str:
        response = self.client.post(
            "/api/uv/projects",
            json={"title": recipe_id, "recipe_id": recipe_id},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["project_id"]

    def test_general_video_is_explicitly_unavailable(self) -> None:
        project_id = self._create("general_video")
        response = self.client.get(f"/api/uv/projects/{project_id}/execution-plan")
        self.assertEqual(response.status_code, 200, response.text)
        plan = response.json()
        self.assertEqual(plan["project_id"], project_id)
        self.assertEqual(plan["compatibility"], "unavailable")
        self.assertFalse(plan["can_prepare_native_execution"])
        self.assertIsNone(plan["target"])
        self.assertIn("narration-led", plan["reason"])

    def test_narrated_video_reports_real_native_contract(self) -> None:
        project_id = self._create("narrated_video")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "available")
        self.assertEqual(plan["target"]["target_id"], "standard")
        self.assertEqual(plan["target"]["launch_path"], "/api/pipelines/standard/tasks")
        self.assertEqual(
            [slot["slot_id"] for slot in plan["runtime_config_slots"]],
            ["llm_model", "image_model", "video_model"],
        )

    def test_action_transfer_preserves_required_production_gates(self) -> None:
        project_id = self._create("action_transfer")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "available")
        self.assertEqual(plan["production_policy"]["source_review"], "required")
        self.assertEqual(plan["production_policy"]["sample_first"], "required")
        self.assertEqual(plan["production_policy"]["final_review"], "required")

    def test_digital_human_reports_partial_instead_of_false_compatibility(self) -> None:
        project_id = self._create("digital_human")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "partial")
        self.assertFalse(plan["can_prepare_native_execution"])
        self.assertIsNone(plan["target"])
        self.assertIn("does not accept", plan["reason"])

    def test_unknown_recovered_recipe_returns_unavailable_plan(self) -> None:
        project = self.store.create_project(
            title="Future recipe",
            recipe_id="future_recipe",
            project_id="prj_future_recipe",
        )
        response = self.client.get(f"/api/uv/projects/{project.project_id}/execution-plan")
        self.assertEqual(response.status_code, 200, response.text)
        plan = response.json()
        self.assertEqual(plan["recipe_id"], "future_recipe")
        self.assertEqual(plan["compatibility"], "unavailable")
        self.assertIn("not installed", plan["reason"])

    def test_missing_project_is_404(self) -> None:
        response = self.client.get("/api/uv/projects/prj_missing/execution-plan")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
