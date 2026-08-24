from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import build_builtin_capability_registry
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class CreativeProjectsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.registry = build_builtin_capability_registry()
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_create_plan_and_update_creative_intent(self) -> None:
        created = self.client.post(
            "/api/uv/creative-projects",
            json={
                "goal": "Сделай минутный ролик про мастерскую керамики",
                "title": "Керамика",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        project = created.json()
        project_id = project["project_id"]
        self.assertEqual(project["title"], "Керамика")
        self.assertEqual(project["recipe_id"], "general_video")
        self.assertEqual(
            project["extensions"]["creative_project"]["goal"],
            "Сделай минутный ролик про мастерскую керамики",
        )

        plan_response = self.client.get(f"/api/uv/projects/{project_id}/creative-plan")
        self.assertEqual(plan_response.status_code, 200, plan_response.text)
        plan = plan_response.json()
        self.assertEqual(plan["project_id"], project_id)
        self.assertEqual(plan["overall_state"], "needs_materials")
        self.assertEqual(
            [phase["phase_id"] for phase in plan["phases"]],
            ["intent", "plan", "visuals", "audio", "assembly", "review"],
        )

        patched = self.client.patch(
            f"/api/uv/projects/{project_id}/creative-intent",
            json={"script": "Открытие мастерской. Работа мастера. Готовые изделия."},
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        self.assertIn(
            "Работа мастера",
            patched.json()["extensions"]["creative_project"]["script"],
        )
        refreshed = self.client.get(f"/api/uv/projects/{project_id}/creative-plan").json()
        self.assertIn("Работа мастера", refreshed["script"])
        plan_phase = next(phase for phase in refreshed["phases"] if phase["phase_id"] == "plan")
        self.assertEqual(plan_phase["state"], "complete")

    def test_creative_plan_rejects_legacy_project(self) -> None:
        project = self.store.create_project(title="Legacy", recipe_id="general_video")
        response = self.client.get(f"/api/uv/projects/{project.project_id}/creative-plan")
        self.assertEqual(response.status_code, 409, response.text)

    def test_empty_update_is_rejected(self) -> None:
        created = self.client.post(
            "/api/uv/creative-projects",
            json={"goal": "Сделай ролик"},
        ).json()
        response = self.client.patch(
            f"/api/uv/projects/{created['project_id']}/creative-intent",
            json={},
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
