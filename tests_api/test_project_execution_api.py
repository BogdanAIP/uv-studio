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

    @staticmethod
    def _assert_capability_projection(plan: dict, capability_id: str) -> None:
        runtime = plan["runtime_config_slots"]
        assert len(runtime) == 1
        assert runtime[0]["capability_id"] == capability_id
        status = runtime[0]["capability_status"]
        assert status["known"] is True
        available = status["offer_summary"]["available"] > 0
        assert plan["compatibility"] == ("available" if available else "partial")
        assert plan["can_prepare_native_execution"] is False
        assert plan["target"] is None

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

    def test_narrated_video_fails_closed_but_preserves_capability_requirements(self) -> None:
        project_id = self._create("narrated_video")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "unavailable")
        self.assertFalse(plan["can_prepare_native_execution"])
        self.assertIsNone(plan["target"])
        self.assertIn("does not mount", plan["reason"])
        self.assertEqual(
            [slot["slot_id"] for slot in plan["runtime_config_slots"]],
            ["llm_model", "image_model", "video_model"],
        )
        for slot in plan["runtime_config_slots"]:
            self.assertTrue(slot["capability_status"]["known"])
            self.assertGreaterEqual(slot["capability_status"]["offer_summary"]["total"], 1)
            self.assertGreaterEqual(
                slot["capability_status"]["offer_summary"]["configuration_required"],
                1,
            )

    def test_action_transfer_fails_closed_and_preserves_required_production_gates(self) -> None:
        project_id = self._create("action_transfer")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "unavailable")
        self.assertFalse(plan["can_prepare_native_execution"])
        self.assertIsNone(plan["target"])
        self.assertIn("not mounted", plan["reason"])
        self.assertEqual(plan["production_policy"]["source_review"], "required")
        self.assertEqual(plan["production_policy"]["sample_first"], "required")
        self.assertEqual(plan["production_policy"]["final_review"], "required")
        runtime = plan["runtime_config_slots"][0]
        self.assertEqual(runtime["capability_id"], "video.action_transfer")
        self.assertEqual(runtime["capability_status"]["offer_summary"]["configuration_required"], 1)

    def test_digital_human_reports_partial_instead_of_false_compatibility(self) -> None:
        project_id = self._create("digital_human")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "partial")
        self.assertFalse(plan["can_prepare_native_execution"])
        self.assertIsNone(plan["target"])
        self.assertIn("does not accept", plan["reason"])

    def test_stage8_story_execution_plan_keeps_media_types_and_no_native_target(self) -> None:
        project_id = self._create("story_video")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "unavailable")
        self.assertFalse(plan["can_prepare_native_execution"])
        self.assertIsNone(plan["target"])
        slots = {slot["slot_id"]: slot for slot in plan["input_slots"]}
        self.assertEqual(slots["brief"]["kind"], "text")
        self.assertEqual(slots["image"]["kind"], "image")
        self.assertEqual(slots["video"]["kind"], "video")
        self.assertEqual(slots["audio"]["kind"], "audio")
        self.assertEqual(plan["production_policy"]["scene_ledger"], "required")

    def test_stage8_commercial_execution_plan_keeps_product_media_types(self) -> None:
        project_id = self._create("commercial_product")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        slots = {slot["slot_id"]: slot for slot in plan["input_slots"]}
        self.assertEqual(plan["compatibility"], "unavailable")
        self.assertEqual(slots["brief"]["kind"], "text")
        self.assertEqual(slots["product_image"]["kind"], "image")
        self.assertEqual(slots["product_video"]["kind"], "video")
        self.assertEqual(slots["audio"]["kind"], "audio")
        self.assertEqual(plan["production_policy"]["sample_first"], "required")

    def test_stage8_photo_execution_plan_projects_semantic_capability_readiness(self) -> None:
        project_id = self._create("photo_to_video")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self._assert_capability_projection(plan, "video.compose_photos")
        slots = {slot["slot_id"]: slot for slot in plan["input_slots"]}
        self.assertEqual(slots["images"]["kind"], "image")
        self.assertTrue(slots["images"]["required"])
        self.assertEqual(slots["audio"]["kind"], "audio")
        self.assertFalse(slots["audio"]["required"])
        self.assertEqual(slots["duration_per_image"]["kind"], "number")
        self.assertEqual(slots["duration_per_image"]["default"], 2.0)
        self.assertIn("video.compose_photos", plan["reason"])

    def test_stage8_visualizer_execution_plan_projects_semantic_capability_readiness(self) -> None:
        project_id = self._create("visualizer")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self._assert_capability_projection(plan, "audio.visualize")
        slots = {slot["slot_id"]: slot for slot in plan["input_slots"]}
        self.assertEqual(slots["audio"]["kind"], "audio")
        self.assertTrue(slots["audio"]["required"])
        self.assertEqual(slots["artwork"]["kind"], "image")
        self.assertFalse(slots["artwork"]["required"])
        self.assertIn("Visualizer", plan["reason"])

    def test_stage8_performance_projects_verified_lipsync_capability_without_fake_target(self) -> None:
        project_id = self._create("performance_lip_sync")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self._assert_capability_projection(plan, "video.digital_human")
        slots = {slot["slot_id"]: slot for slot in plan["input_slots"]}
        self.assertEqual(slots["portrait"]["kind"], "image")
        self.assertEqual(slots["speech"]["kind"], "audio")
        self.assertEqual(slots["performance_video"]["kind"], "video")
        self.assertIn("Performance/lip-sync", plan["reason"])

    def test_stage8_free_project_has_no_required_inputs_or_native_target(self) -> None:
        project_id = self._create("free_project")
        plan = self.client.get(f"/api/uv/projects/{project_id}/execution-plan").json()
        self.assertEqual(plan["compatibility"], "unavailable")
        self.assertFalse(plan["can_prepare_native_execution"])
        self.assertIsNone(plan["target"])
        self.assertTrue(plan["input_slots"])
        self.assertTrue(all(not slot["required"] for slot in plan["input_slots"]))
        self.assertEqual(
            [slot["kind"] for slot in plan["input_slots"]],
            ["text", "image", "video", "audio"],
        )

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