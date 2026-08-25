from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.project_common import get_project_store
from uv_studio.generation.test_support import TEST_GENERATION_ENV, TEST_MODEL_ID
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class NamedGenerationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_test_generation = os.environ.get(TEST_GENERATION_ENV)
        os.environ[TEST_GENERATION_ENV] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

        created = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Stage 14 API", "direction_id": "micro_drama"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]

        scene = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/production/commands",
            json={
                "command": "create_scene",
                "scene_id": "scene_generation_api",
                "title": "Generated scene",
                "summary": "API vertical",
            },
        )
        self.assertEqual(scene.status_code, 201, scene.text)
        shot = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/production/commands",
            json={
                "command": "create_shot",
                "shot_id": "shot_generation_api",
                "scene_id": "scene_generation_api",
                "intent": "Generate one controlled image",
                "reference_ids": [],
            },
        )
        self.assertEqual(shot.status_code, 201, shot.text)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()
        if self.previous_test_generation is None:
            os.environ.pop(TEST_GENERATION_ENV, None)
        else:
            os.environ[TEST_GENERATION_ENV] = self.previous_test_generation

    def _request(self, prompt: str = "portrait") -> dict:
        return {
            "shot_id": "shot_generation_api",
            "model_id": TEST_MODEL_ID,
            "inputs": {"prompt": prompt, "seed": 14},
            "contract": {
                "fixed_constraints": ["same character"],
                "editable_variables": ["camera"],
                "forbidden_changes": ["identity"],
                "approved_reference_id": None,
            },
        }

    def test_test_model_is_strictly_environment_gated(self) -> None:
        enabled = self.client.get("/api/uv/models")
        self.assertEqual(enabled.status_code, 200, enabled.text)
        enabled_ids = [item["model_id"] for item in enabled.json()]
        self.assertIn(TEST_MODEL_ID, enabled_ids)
        self.assertIn("uv.image.standard", enabled_ids)

        os.environ.pop(TEST_GENERATION_ENV, None)
        disabled = self.client.get("/api/uv/models")
        self.assertEqual(disabled.status_code, 200, disabled.text)
        disabled_ids = [item["model_id"] for item in disabled.json()]
        self.assertNotIn(TEST_MODEL_ID, disabled_ids)
        standard = next(item for item in disabled.json() if item["model_id"] == "uv.image.standard")
        self.assertEqual(standard["execution"]["availability"], "configuration_required")
        os.environ[TEST_GENERATION_ENV] = "1"

    def test_prepare_submit_replay_conflict_and_fresh_reroll(self) -> None:
        request = self._request()
        prepared = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/generation/prepare",
            json=request,
        )
        self.assertEqual(prepared.status_code, 200, prepared.text)
        preparation = prepared.json()
        self.assertEqual(preparation["model"]["model_id"], TEST_MODEL_ID)
        self.assertEqual(preparation["model"]["execution"]["availability"], "available")
        self.assertFalse(preparation["authorization"]["authorization_required"])

        first = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/generation/jobs",
            json={**request, "idempotency_key": "idem_generation_api"},
        )
        self.assertEqual(first.status_code, 202, first.text)
        first_job_id = first.json()["job"]["job_id"]
        self.assertFalse(first.json()["reused"])

        job = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/generation/jobs/{first_job_id}"
        )
        self.assertEqual(job.status_code, 200, job.text)
        completed = job.json()
        self.assertEqual(completed["status"], "succeeded")
        self.assertEqual(len(completed["attempts"]), 1)
        artifact_id = completed["attempts"][0]["output_reference_id"]
        take_id = completed["attempts"][0]["take_id"]
        self.assertIsNotNone(artifact_id)
        self.assertIsNotNone(take_id)

        project = self.client.get(f"/api/uv/projects/{self.project_id}")
        self.assertEqual(project.status_code, 200, project.text)
        artifact = next(item for item in project.json()["artifacts"] if item["id"] == artifact_id)
        self.assertEqual(artifact["metadata"]["generation"]["job_id"], first_job_id)
        self.assertEqual(artifact["metadata"]["generation"]["model_id"], TEST_MODEL_ID)
        self.assertTrue(artifact["metadata"]["executor"]["test_only"])

        production = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/production"
        )
        self.assertEqual(production.status_code, 200, production.text)
        shot = production.json()["shots"][0]
        self.assertEqual(shot["take_ids"], [take_id])
        self.assertIsNone(shot["accepted_take_id"])

        replay = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/generation/jobs",
            json={**request, "idempotency_key": "idem_generation_api"},
        )
        self.assertEqual(replay.status_code, 202, replay.text)
        self.assertTrue(replay.json()["reused"])
        self.assertEqual(replay.json()["job"]["job_id"], first_job_id)
        self.assertEqual(len(replay.json()["job"]["attempts"]), 1)

        conflict = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/generation/jobs",
            json={**self._request("different prompt"), "idempotency_key": "idem_generation_api"},
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["detail"]["code"], "generation_job_conflict")

        reroll = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/generation/jobs",
            json={**request, "idempotency_key": "idem_generation_api_reroll"},
        )
        self.assertEqual(reroll.status_code, 202, reroll.text)
        self.assertFalse(reroll.json()["reused"])
        self.assertNotEqual(reroll.json()["job"]["job_id"], first_job_id)

        jobs = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/generation/jobs"
        )
        self.assertEqual(jobs.status_code, 200, jobs.text)
        self.assertEqual(len(jobs.json()), 2)
        self.assertEqual({item["status"] for item in jobs.json()}, {"succeeded"})


if __name__ == "__main__":
    unittest.main()
