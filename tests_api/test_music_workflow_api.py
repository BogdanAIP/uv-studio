from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class MusicWorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post(
            "/api/uv/projects",
            json={"title": "Music Product Orchestrator", "recipe_id": "music_video"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]
        self._source("song", "audio", b"music-workflow-song", 10_000_000, ".wav")
        self._source("clip_a", "video", b"music-workflow-video-a", 8_000_000, ".mp4")
        self._source("clip_b", "video", b"music-workflow-video-b", 8_000_000, ".mp4")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _source(
        self,
        source_id: str,
        kind: str,
        payload: bytes,
        duration_us: int,
        suffix: str,
    ) -> None:
        relative = f"sources/{source_id}{suffix}"
        (self.store.project_directory(self.project_id) / relative).write_bytes(payload)
        reference = ProjectReference(
            id=source_id,
            kind=kind,
            path=relative,
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": duration_us,
            },
        )
        project = self.store.load_project(self.project_id)
        self.store.update_project(self.project_id, sources=(*project.sources, reference))

    def _workflow(self) -> dict:
        response = self.client.get(f"/api/uv/projects/{self.project_id}/workflow")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    @staticmethod
    def _action(state: dict, action_id: str) -> dict:
        return next(item for item in state["next_actions"] if item["action_id"] == action_id)

    def test_music_map_direction_and_assembly_use_product_orchestrator(self) -> None:
        initial = self._workflow()
        self.assertEqual(initial["recipe_id"], "music_video")
        self.assertEqual(initial["relevant_workspaces"][0]["workspace_id"], "music_video")
        save_map = self._action(initial, "save_music_map")
        self.assertTrue(save_map["enabled"])
        self.assertEqual(save_map["input_schema"]["properties"]["song_reference_id"]["enum"], ["song"])

        map_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/workflow/actions/save_music_map",
            json={
                "song_reference_id": "song",
                "excerpt": {"start_us": 0, "end_us": 10_000_000},
                "sections": [
                    {
                        "section_id": "whole",
                        "kind": "other",
                        "label": "Whole",
                        "start_us": 0,
                        "end_us": 10_000_000,
                    }
                ],
                "markers": [
                    {"marker_id": "cut", "kind": "cut_point", "time_us": 5_000_000}
                ],
                "lyric_phrases": [],
            },
        )
        self.assertEqual(map_response.status_code, 200, map_response.text)
        map_revision = map_response.json()["result"]["revision_sha256"]

        after_map = self._workflow()
        save_direction = self._action(after_map, "save_music_direction")
        self.assertTrue(save_direction["enabled"])
        self.assertEqual(
            save_direction["suggested_input"]["music_map_revision_sha256"],
            map_revision,
        )

        direction_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/workflow/actions/save_music_direction",
            json={
                "music_map_revision_sha256": map_revision,
                "shots": [
                    {
                        "shot_id": "shot_a",
                        "order": 0,
                        "start_us": 0,
                        "end_us": 5_000_000,
                        "intent": "First visual",
                        "sync_marker_ids": ["cut"],
                        "transition_out": "cut",
                    },
                    {
                        "shot_id": "shot_b",
                        "order": 1,
                        "start_us": 5_000_000,
                        "end_us": 10_000_000,
                        "intent": "Second visual",
                        "sync_marker_ids": [],
                        "transition_out": "fade",
                    },
                ],
            },
        )
        self.assertEqual(direction_response.status_code, 200, direction_response.text)
        direction_revision = direction_response.json()["result"]["revision_sha256"]

        after_direction = self._workflow()
        save_assembly = self._action(after_direction, "save_music_assembly")
        self.assertTrue(save_assembly["enabled"])
        self.assertEqual(
            save_assembly["suggested_input"]["music_direction_revision_sha256"],
            direction_revision,
        )

        assembly_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/workflow/actions/save_music_assembly",
            json={
                "music_direction_revision_sha256": direction_revision,
                "assignments": [
                    {"shot_id": "shot_a", "source_id": "clip_a", "source_start_us": 0},
                    {"shot_id": "shot_b", "source_id": "clip_b", "source_start_us": 0},
                ],
            },
        )
        self.assertEqual(assembly_response.status_code, 200, assembly_response.text)
        assembly_revision = assembly_response.json()["result"]["revision_sha256"]

        after_assembly = self._workflow()
        render = self._action(after_assembly, "render_music_master")
        self.assertEqual(
            render["suggested_input"].get("assembly_revision_sha256"),
            assembly_revision,
        )
        self.assertTrue(
            next(
                item
                for item in after_assembly["prerequisites"]
                if item["prerequisite_id"] == "music.rhythm_aligned"
            )["satisfied"]
        )

    def test_stale_revision_and_tampered_video_fail_closed(self) -> None:
        map_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/workflow/actions/save_music_map",
            json={
                "song_reference_id": "song",
                "excerpt": {"start_us": 0, "end_us": 10_000_000},
                "sections": [
                    {
                        "section_id": "whole",
                        "kind": "other",
                        "label": "Whole",
                        "start_us": 0,
                        "end_us": 10_000_000,
                    }
                ],
                "markers": [],
                "lyric_phrases": [],
            },
        )
        self.assertEqual(map_response.status_code, 200, map_response.text)
        current_revision = map_response.json()["result"]["revision_sha256"]

        stale = self.client.post(
            f"/api/uv/projects/{self.project_id}/workflow/actions/save_music_direction",
            json={
                "music_map_revision_sha256": "0" * 64,
                "shots": [
                    {
                        "shot_id": "whole",
                        "order": 0,
                        "start_us": 0,
                        "end_us": 10_000_000,
                        "intent": "Whole excerpt",
                        "sync_marker_ids": [],
                        "transition_out": "fade",
                    }
                ],
            },
        )
        self.assertEqual(stale.status_code, 422, stale.text)
        self.assertEqual(stale.json()["detail"]["code"], "workflow_action_input_rejected")

        direction = self.client.post(
            f"/api/uv/projects/{self.project_id}/workflow/actions/save_music_direction",
            json={
                "music_map_revision_sha256": current_revision,
                "shots": [
                    {
                        "shot_id": "whole",
                        "order": 0,
                        "start_us": 0,
                        "end_us": 10_000_000,
                        "intent": "Whole excerpt",
                        "sync_marker_ids": [],
                        "transition_out": "fade",
                    }
                ],
            },
        )
        self.assertEqual(direction.status_code, 200, direction.text)

        project = self.store.load_project(self.project_id)
        clip = next(item for item in project.sources if item.id == "clip_a")
        (self.store.project_directory(self.project_id) / clip.path).write_bytes(b"tampered")
        state = self._workflow()
        source_prerequisite = next(
            item for item in state["prerequisites"] if item["prerequisite_id"] == "source.video"
        )
        self.assertTrue(source_prerequisite["satisfied"])
        save_assembly = self._action(state, "save_music_assembly")
        source_enum = save_assembly["input_schema"].get("properties", {}).get("assignments", {})
        self.assertNotIn("clip_a", str(source_enum))
        self.assertTrue(any(item["code"] == "music_video_source_unverified" for item in state["diagnostics"]))


if __name__ == "__main__":
    unittest.main()
