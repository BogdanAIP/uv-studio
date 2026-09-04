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


class MusicMapApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        self.project_id = self.store.create_project(
            title="Music API",
            recipe_id="music_video",
        ).project_id
        self.project_dir = self.store.project_directory(self.project_id)
        self._register_audio()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _register_audio(self) -> None:
        payload = b"api-music-audio"
        path = self.project_dir / "sources" / "song.wav"
        path.write_bytes(payload)
        reference = ProjectReference(
            id="song",
            kind="audio",
            path="sources/song.wav",
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": 30_000_000,
            },
        )
        project = self.store.load_project(self.project_id)
        self.store.update_project(self.project_id, sources=(*project.sources, reference))

    def test_music_map_semantic_command_roundtrip(self) -> None:
        empty = self.client.get(f"/api/uv/projects/{self.project_id}/music-map")
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json(), {"music_map": None})

        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-map/commands",
            json={
                "command": "set_music_map",
                "song_reference_id": "song",
                "excerpt": {"start_us": 2_000_000, "end_us": 27_000_000},
                "sections": [
                    {
                        "section_id": "verse",
                        "kind": "verse",
                        "label": "Verse",
                        "start_us": 2_000_000,
                        "end_us": 12_000_000,
                    },
                    {
                        "section_id": "chorus",
                        "kind": "chorus",
                        "label": "Chorus",
                        "start_us": 12_000_000,
                        "end_us": 27_000_000,
                    },
                ],
                "markers": [
                    {"marker_id": "downbeat", "kind": "downbeat", "time_us": 4_000_000},
                    {"marker_id": "peak", "kind": "climax", "time_us": 20_000_000},
                ],
                "lyric_phrases": [
                    {
                        "phrase_id": "line_1",
                        "start_us": 3_000_000,
                        "end_us": 6_500_000,
                        "text": "First line",
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()["payload"]
        self.assertEqual(payload["song"]["reference_id"], "song")
        self.assertEqual(payload["excerpt"]["end_us"] - payload["excerpt"]["start_us"], 25_000_000)
        self.assertEqual(len(payload["revision_sha256"]), 64)

        reopened = self.client.get(f"/api/uv/projects/{self.project_id}/music-map")
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["music_map"]["revision_sha256"], payload["revision_sha256"])

        cleared = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-map/commands",
            json={"command": "clear_music_map"},
        )
        self.assertEqual(cleared.status_code, 201, cleared.text)
        self.assertIsNone(cleared.json()["payload"])
        self.assertEqual(
            self.client.get(f"/api/uv/projects/{self.project_id}/music-map").json(),
            {"music_map": None},
        )

    def test_invalid_music_map_is_422_and_missing_project_is_404(self) -> None:
        invalid = self.client.post(
            f"/api/uv/projects/{self.project_id}/music-map/commands",
            json={
                "command": "set_music_map",
                "song_reference_id": "song",
                "excerpt": {"start_us": 0, "end_us": 5_000_000},
                "sections": [],
                "markers": [
                    {"marker_id": "outside", "kind": "beat", "time_us": 5_000_000}
                ],
                "lyric_phrases": [],
            },
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)
        self.assertIn("half-open excerpt", invalid.json()["detail"])

        missing = self.client.get("/api/uv/projects/missing_project/music-map")
        self.assertEqual(missing.status_code, 404, missing.text)


if __name__ == "__main__":
    unittest.main()
