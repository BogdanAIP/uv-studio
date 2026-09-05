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
    RETIRED_ACTIONS = (
        "save_music_map",
        "save_music_direction",
        "save_music_assembly",
        "render_music_master",
        "review_music_master",
    )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        self.project_id = self.store.create_project(
            title="Music read-only Product Workflow",
            recipe_id="music_video",
        ).project_id
        self._source("song", "audio", b"music-workflow-song", 10_000_000, ".wav")
        self._source("clip_a", "video", b"music-workflow-video-a", 12_000_000, ".mp4")
        self._source("clip_b", "video", b"music-workflow-video-b", 12_000_000, ".mp4")

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
    def _prerequisite(state: dict, prerequisite_id: str) -> dict:
        return next(
            item
            for item in state["prerequisites"]
            if item["prerequisite_id"] == prerequisite_id
        )

    def test_music_product_workflow_is_read_only_and_old_actions_fail_closed(self) -> None:
        state = self._workflow()
        self.assertEqual(state["recipe_id"], "music_video")
        self.assertEqual(state["relevant_workspaces"][0]["workspace_id"], "music_video")
        self.assertEqual(state["next_actions"], [])
        self.assertTrue(self._prerequisite(state, "source.audio")["satisfied"])
        self.assertFalse(self._prerequisite(state, "music.map")["satisfied"])

        for action_id in self.RETIRED_ACTIONS:
            with self.subTest(action_id=action_id):
                response = self.client.post(
                    f"/api/uv/projects/{self.project_id}/workflow/actions/{action_id}",
                    json={"image_source_ids": ["clip_a"]},
                )
                self.assertEqual(response.status_code, 404, response.text)
                self.assertEqual(
                    response.json()["detail"],
                    "Workflow action not found for this project",
                )

    def test_direct_music_domain_changes_remain_visible_in_read_projection(self) -> None:
        map_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-map/commands",
            json={
                "command": "set_music_map",
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
        self.assertEqual(map_response.status_code, 201, map_response.text)
        map_revision = map_response.json()["payload"]["revision_sha256"]

        after_map = self._workflow()
        self.assertEqual(after_map["next_actions"], [])
        self.assertTrue(self._prerequisite(after_map, "music.map")["satisfied"])

        direction_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-direction/commands",
            json={
                "command": "set_music_direction",
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
        self.assertEqual(direction_response.status_code, 201, direction_response.text)
        direction_revision = direction_response.json()["payload"]["revision_sha256"]

        after_direction = self._workflow()
        self.assertEqual(after_direction["next_actions"], [])
        self.assertTrue(self._prerequisite(after_direction, "music.direction")["satisfied"])
        self.assertTrue(
            self._prerequisite(after_direction, "music.rhythm_aligned")["satisfied"]
        )

        assembly_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-assembly/commands",
            json={
                "command": "set_music_assembly",
                "music_direction_revision_sha256": direction_revision,
                "assignments": [
                    {"shot_id": "shot_a", "source_id": "clip_a", "source_start_us": 0},
                    {"shot_id": "shot_b", "source_id": "clip_b", "source_start_us": 0},
                ],
            },
        )
        self.assertEqual(assembly_response.status_code, 201, assembly_response.text)

        after_assembly = self._workflow()
        self.assertEqual(after_assembly["next_actions"], [])
        self.assertTrue(self._prerequisite(after_assembly, "music.assembly")["satisfied"])

        clip = next(
            item
            for item in self.store.load_project(self.project_id).sources
            if item.id == "clip_a"
        )
        (self.store.project_directory(self.project_id) / clip.path).write_bytes(b"tampered")

        tampered = self._workflow()
        self.assertEqual(tampered["next_actions"], [])
        self.assertTrue(
            any(
                item["code"] == "music_video_source_unverified"
                for item in tampered["diagnostics"]
            )
        )
        self.assertFalse(self._prerequisite(tampered, "music.assembly")["satisfied"])


if __name__ == "__main__":
    unittest.main()
