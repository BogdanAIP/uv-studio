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


class MusicDirectionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post(
            "/api/uv/projects",
            json={"title": "Music direction API", "recipe_id": "music_video"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]
        project_dir = self.store.project_directory(self.project_id)
        payload = b"direction-api-audio"
        (project_dir / "sources" / "song.wav").write_bytes(payload)
        reference = ProjectReference(
            id="song",
            kind="audio",
            path="sources/song.wav",
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": 25_000_000,
            },
        )
        current = self.store.load_project(self.project_id)
        self.store.update_project(self.project_id, sources=(*current.sources, reference))
        music = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-map/commands",
            json={
                "command": "set_music_map",
                "song_reference_id": "song",
                "excerpt": {"start_us": 0, "end_us": 20_000_000},
                "sections": [
                    {
                        "section_id": "verse",
                        "kind": "verse",
                        "label": "Verse",
                        "start_us": 0,
                        "end_us": 10_000_000,
                    },
                    {
                        "section_id": "chorus",
                        "kind": "chorus",
                        "label": "Chorus",
                        "start_us": 10_000_000,
                        "end_us": 20_000_000,
                    },
                ],
                "markers": [
                    {"marker_id": "cut_a", "kind": "downbeat", "time_us": 5_000_000},
                    {"marker_id": "cut_b", "kind": "beat", "time_us": 10_000_000},
                ],
                "lyric_phrases": [],
            },
        )
        self.assertEqual(music.status_code, 201, music.text)
        self.music_revision = music.json()["payload"]["revision_sha256"]

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_direction_and_rhythm_audit_roundtrip(self) -> None:
        empty = self.client.get(f"/api/uv/projects/{self.project_id}/music-direction")
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json(), {"music_direction": None})

        created = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-direction/commands",
            json={
                "command": "set_music_direction",
                "music_map_revision_sha256": self.music_revision,
                "shots": [
                    {
                        "shot_id": "shot_1",
                        "order": 0,
                        "start_us": 0,
                        "end_us": 5_050_000,
                        "intent": "Open on performer.",
                        "sync_marker_ids": ["cut_a"],
                        "transition_out": "cut",
                    },
                    {
                        "shot_id": "shot_2",
                        "order": 1,
                        "start_us": 5_050_000,
                        "end_us": 10_250_000,
                        "intent": "Enter chorus.",
                        "sync_marker_ids": ["cut_b"],
                        "transition_out": "match_cut",
                    },
                    {
                        "shot_id": "shot_3",
                        "order": 2,
                        "start_us": 10_250_000,
                        "end_us": 20_000_000,
                        "intent": "Finish excerpt.",
                        "sync_marker_ids": [],
                        "transition_out": "fade",
                    },
                ],
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["payload"]["music_map_revision_sha256"], self.music_revision)

        audit = self.client.get(
            f"/api/uv/projects/{self.project_id}/music-direction/rhythm-audit",
            params={"tolerance_us": 120_000},
        )
        self.assertEqual(audit.status_code, 200, audit.text)
        body = audit.json()
        self.assertEqual(body["cuts"][0]["delta_us"], 50_000)
        self.assertTrue(body["cuts"][0]["aligned"])
        self.assertEqual(body["cuts"][1]["delta_us"], 250_000)
        self.assertFalse(body["cuts"][1]["aligned"])
        self.assertEqual(body["summary"]["aligned_count"], 1)

    def test_stale_revision_and_unknown_marker_fail_422(self) -> None:
        stale = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-direction/commands",
            json={
                "command": "set_music_direction",
                "music_map_revision_sha256": "0" * 64,
                "shots": [
                    {
                        "shot_id": "shot_1",
                        "order": 0,
                        "start_us": 0,
                        "end_us": 20_000_000,
                        "intent": "Whole excerpt.",
                        "sync_marker_ids": [],
                        "transition_out": "cut",
                    }
                ],
            },
        )
        self.assertEqual(stale.status_code, 422, stale.text)
        self.assertIn("stale Music Map", stale.json()["detail"])

        unknown = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-direction/commands",
            json={
                "command": "set_music_direction",
                "music_map_revision_sha256": self.music_revision,
                "shots": [
                    {
                        "shot_id": "shot_1",
                        "order": 0,
                        "start_us": 0,
                        "end_us": 20_000_000,
                        "intent": "Whole excerpt.",
                        "sync_marker_ids": ["missing"],
                        "transition_out": "cut",
                    }
                ],
            },
        )
        self.assertEqual(unknown.status_code, 422, unknown.text)
        self.assertIn("unknown sync marker", unknown.json()["detail"])


if __name__ == "__main__":
    unittest.main()
