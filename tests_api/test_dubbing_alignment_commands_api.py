from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.prepared_audio import ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class DubbingAlignmentCommandsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"recipe_id": "general_video", "title": "Alignment API"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]
        self.source = self._source()
        self.audio = self._audio()
        self.dubbing_id = self._transcript()
        self.take_id = self._take()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _source(self):
        store = ProjectSourceMediaStore(self.store)
        allocation = store.allocate(self.project_id, "source.mkv")
        body = b"alignment-source"
        allocation.absolute_path.write_bytes(body)
        project = store.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "source.mkv",
                "content_type": "video/x-matroska",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 8_000_000,
                "has_audio": True,
                "width": 1280,
                "height": 720,
            },
        )
        return next(item for item in project.sources if item.id == allocation.source_id)

    def _audio(self):
        store = ProjectPreparedAudioStore(self.store)
        allocation = store.allocate(self.project_id, "voice.wav")
        body = b"alignment-audio"
        allocation.absolute_path.write_bytes(body)
        project = store.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "voice.wav",
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 1_900_000,
                "has_audio": True,
                "has_video": False,
                "origin": "recorded",
            },
        )
        return next(item for item in project.artifacts if item.id == allocation.audio_id)

    def _transcript(self) -> str:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en-US",
                "start_us": 1_000_000,
                "end_us": 6_000_000,
                "segments": [
                    {
                        "segment_id": "seg_1",
                        "start_us": 2_000_000,
                        "end_us": 4_000_000,
                        "text": "Hello world",
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["dubbing_id"]

    def _take(self) -> str:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "attach_prepared_speech",
                "dubbing_id": self.dubbing_id,
                "audio_id": self.audio.id,
                "segment_id": "seg_1",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["payload"]["prepared_speech"]["take_id"]

    def test_accept_alignment_derives_revision_language_and_target_range_from_current_take(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_alignment",
                "take_id": self.take_id,
                "marks": [
                    {
                        "mark_id": "mark_000001",
                        "unit": "word",
                        "text": "Hello",
                        "audio_start_us": 100_000,
                        "audio_end_us": 650_000,
                        "confidence": 0.94,
                    },
                    {
                        "mark_id": "mark_000002",
                        "unit": "word",
                        "text": "world",
                        "audio_start_us": 700_000,
                        "audio_end_us": 1_400_000,
                        "confidence": 0.91,
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        alignment = response.json()["payload"]["alignment"]
        self.assertTrue(alignment["alignment_id"].startswith("align_"))
        self.assertEqual(alignment["take_id"], self.take_id)
        self.assertEqual(alignment["dubbing_id"], self.dubbing_id)
        self.assertEqual(alignment["audio_id"], self.audio.id)
        self.assertEqual(alignment["language"], "en-us")
        self.assertEqual(alignment["segment_id"], "seg_1")
        self.assertEqual(alignment["target_start_us"], 2_000_000)
        self.assertEqual(alignment["target_end_us"], 4_000_000)
        self.assertEqual(len(alignment["take_sha256"]), 64)
        self.assertEqual(alignment["marks"][0]["text"], "Hello")

        state = self.client.get(f"/api/uv/projects/{self.project_id}/editor/state")
        self.assertEqual(state.status_code, 200, state.text)
        self.assertEqual(
            state.json()["dubbing_alignments"]["alignments"][0]["alignment_id"],
            alignment["alignment_id"],
        )

    def test_client_cannot_supply_script_audio_source_or_target_revision_bindings(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_alignment",
                "take_id": self.take_id,
                "script_sha256": "f" * 64,
                "audio_sha256": "f" * 64,
                "source_path": "C:/outside/source.mkv",
                "target_start_us": 0,
                "target_end_us": 999_000_000,
                "provider": "remote.magic",
                "marks": [
                    {
                        "mark_id": "mark_1",
                        "unit": "word",
                        "text": "Hello",
                        "audio_start_us": 100_000,
                        "audio_end_us": 600_000,
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_alignment_mark_outside_prepared_audio_duration_is_rejected(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_alignment",
                "take_id": self.take_id,
                "marks": [
                    {
                        "mark_id": "mark_long",
                        "unit": "word",
                        "text": "world",
                        "audio_start_us": 1_800_000,
                        "audio_end_us": 2_100_000,
                        "confidence": 0.8,
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        state = self.client.get(f"/api/uv/projects/{self.project_id}/editor/state")
        self.assertEqual(state.status_code, 200, state.text)
        self.assertEqual(state.json()["dubbing_alignments"]["alignments"], [])


if __name__ == "__main__":
    unittest.main()
