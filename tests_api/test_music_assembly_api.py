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


class MusicAssemblyApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        self.project_id = self.store.create_project(
            title="Music assembly API",
            recipe_id="music_video",
        ).project_id
        self._source("song", "audio", b"assembly-api-song", 10_000_000, ".wav")
        self._source("clip_a", "video", b"assembly-api-video-a", 8_000_000, ".mp4")
        self._source("clip_b", "video", b"assembly-api-video-b", 8_000_000, ".mp4")

        music = self.client.post(
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
        self.assertEqual(music.status_code, 201, music.text)
        direction = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-direction/commands",
            json={
                "command": "set_music_direction",
                "music_map_revision_sha256": music.json()["payload"]["revision_sha256"],
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
        self.assertEqual(direction.status_code, 201, direction.text)
        self.direction_revision = direction.json()["payload"]["revision_sha256"]

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

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_assembly_roundtrip_and_clear(self) -> None:
        empty = self.client.get(f"/api/uv/projects/{self.project_id}/music-assembly")
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json(), {"music_assembly": None})

        created = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-assembly/commands",
            json={
                "command": "set_music_assembly",
                "music_direction_revision_sha256": self.direction_revision,
                "assignments": [
                    {"shot_id": "shot_b", "source_id": "clip_b", "source_start_us": 0},
                    {"shot_id": "shot_a", "source_id": "clip_a", "source_start_us": 1_000_000},
                ],
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        payload = created.json()["payload"]
        self.assertEqual([item["shot_id"] for item in payload["bindings"]], ["shot_a", "shot_b"])
        self.assertEqual(payload["bindings"][0]["source_end_us"], 6_000_000)

        reopened = self.client.get(f"/api/uv/projects/{self.project_id}/music-assembly")
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["music_assembly"]["revision_sha256"], payload["revision_sha256"])

        cleared = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-assembly/commands",
            json={"command": "clear_music_assembly"},
        )
        self.assertEqual(cleared.status_code, 201, cleared.text)
        self.assertIsNone(cleared.json()["payload"])

    def test_stale_or_incomplete_plan_fails_422(self) -> None:
        stale = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-assembly/commands",
            json={
                "command": "set_music_assembly",
                "music_direction_revision_sha256": "0" * 64,
                "assignments": [
                    {"shot_id": "shot_a", "source_id": "clip_a", "source_start_us": 0},
                    {"shot_id": "shot_b", "source_id": "clip_b", "source_start_us": 0},
                ],
            },
        )
        self.assertEqual(stale.status_code, 422, stale.text)
        self.assertIn("stale Music Director", stale.json()["detail"])

        incomplete = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-assembly/commands",
            json={
                "command": "set_music_assembly",
                "music_direction_revision_sha256": self.direction_revision,
                "assignments": [
                    {"shot_id": "shot_a", "source_id": "clip_a", "source_start_us": 0}
                ],
            },
        )
        self.assertEqual(incomplete.status_code, 422, incomplete.text)
        self.assertIn("exactly every", incomplete.json()["detail"])

    def test_substituted_source_bytes_make_get_fail_closed(self) -> None:
        created = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-assembly/commands",
            json={
                "command": "set_music_assembly",
                "music_direction_revision_sha256": self.direction_revision,
                "assignments": [
                    {"shot_id": "shot_a", "source_id": "clip_a", "source_start_us": 0},
                    {"shot_id": "shot_b", "source_id": "clip_b", "source_start_us": 0},
                ],
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        binding = created.json()["payload"]["bindings"][0]
        (self.store.project_directory(self.project_id) / binding["source_path"]).write_bytes(
            b"substituted"
        )
        reopened = self.client.get(f"/api/uv/projects/{self.project_id}/music-assembly")
        self.assertEqual(reopened.status_code, 422, reopened.text)


if __name__ == "__main__":
    unittest.main()
