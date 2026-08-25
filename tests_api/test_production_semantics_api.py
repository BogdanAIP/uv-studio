from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.project_common import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class ProductionSemanticsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

        created = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Micro Drama API", "direction_id": "micro_drama"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]

        self.references = []
        for number, duration in ((1, 4_000_000), (2, 5_000_000)):
            path = self.store.resolve_project_file(
                self.project_id,
                f"assets/api_take_{number}.mp4",
                allowed_roots=("assets",),
            )
            path.write_bytes(f"take-{number}".encode())
            self.references.append(
                ProjectReference(
                    id=f"asset_api_take_{number}",
                    kind="video",
                    path=f"assets/api_take_{number}.mp4",
                    metadata={"duration_us": duration},
                )
            )
        self.store.update_project(
            self.project_id,
            artifacts=tuple(self.references),
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _command(self, payload: dict) -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/production/commands",
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_micro_drama_user_flow_reaches_canonical_timeline_through_one_api(self) -> None:
        empty = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/production"
        )
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json()["scenes"], [])

        self._command(
            {
                "command": "create_scene",
                "scene_id": "scene_api",
                "title": "API scene",
                "summary": "Opening beat",
            }
        )
        self._command(
            {
                "command": "create_shot",
                "shot_id": "shot_api",
                "scene_id": "scene_api",
                "intent": "Close reaction shot",
                "reference_ids": [self.references[0].id],
            }
        )
        for number, reference in enumerate(self.references, start=1):
            self._command(
                {
                    "command": "register_take",
                    "take_id": f"take_api_{number}",
                    "shot_id": "shot_api",
                    "reference_id": reference.id,
                    "label": f"Candidate {number}",
                }
            )

        context = self._command(
            {
                "command": "set_micro_drama_context",
                "document": {
                    "story": {
                        "title": "API Story",
                        "premise": "A short premise",
                    },
                    "characters": [
                        {
                            "character_id": "char_api",
                            "name": "Hero",
                        }
                    ],
                    "locations": [
                        {
                            "location_id": "loc_api",
                            "name": "Room",
                        }
                    ],
                    "scene_continuity": [
                        {
                            "scene_id": "scene_api",
                            "character_ids": ["char_api"],
                            "location_id": "loc_api",
                            "canon_facts": ["Hero holds the key"],
                        }
                    ],
                },
            }
        )
        self.assertEqual(context["micro_drama"]["story"]["title"], "API Story")

        accepted = self._command(
            {
                "command": "accept_take",
                "take_id": "take_api_2",
                "timeline_start_us": 0,
                "source_start_us": 500_000,
                "duration_us": 3_000_000,
                "track_id": "trk_api_story",
                "clip_id": "clip_api_story",
            }
        )
        shot = accepted["production"]["shots"][0]
        self.assertEqual(shot["accepted_take_id"], "take_api_2")
        self.assertEqual(shot["timeline_clip_ids"], ["clip_api_story"])
        self.assertEqual(
            accepted["timeline"]["tracks"][0]["clips"][0]["reference_id"],
            self.references[1].id,
        )

        production = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/production"
        )
        self.assertEqual(production.status_code, 200, production.text)
        self.assertEqual(
            production.json()["shots"][0]["accepted_take_id"],
            "take_api_2",
        )
        micro = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/production/micro-drama"
        )
        self.assertEqual(micro.status_code, 200, micro.text)
        self.assertEqual(
            micro.json()["scene_continuity"][0]["canon_facts"],
            ["Hero holds the key"],
        )

        timeline = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/timeline"
        )
        self.assertEqual(timeline.status_code, 200, timeline.text)
        self.assertEqual(
            timeline.json()["tracks"][0]["clips"][0]["clip_id"],
            "clip_api_story",
        )

    def test_micro_drama_context_is_rejected_for_other_direction(self) -> None:
        created = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Commercial API", "direction_id": "commercial"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        project_id = created.json()["project_id"]
        response = self.client.post(
            f"/api/uv/projects/{project_id}/studio/production/commands",
            json={
                "command": "set_micro_drama_context",
                "document": {"story": {"title": "Wrong direction"}},
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("requires direction_id='micro_drama'", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
