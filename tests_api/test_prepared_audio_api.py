from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.prepared_audio import (
    MAX_PREPARED_AUDIO_UPLOAD_BYTES,
    get_prepared_audio_probe,
)
from uv_studio.api.projects import get_project_store
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class PreparedAudioApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_prepared_audio_probe] = lambda: self._probe
        self.client = TestClient(app)
        self.project_id = self.store.create_project(
            recipe_id="general_video",
            title="Prepared speech",
        ).project_id

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _probe(_store, _project_id, relative_path):
        return {
            "path": relative_path,
            "duration_us": 2_750_000,
            "format_name": "wav",
            "has_video": False,
            "has_audio": True,
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "pcm_s16le",
                    "sample_fmt": "s16",
                    "sample_rate": "48000",
                    "channels": 1,
                    "channel_layout": "mono",
                }
            ],
        }

    def test_upload_registers_project_owned_audio_and_supports_range_streaming(self) -> None:
        body = b"RIFF-prepared-speech-bytes"
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/prepared-audio",
            params={"filename": "C:\\recordings\\take-01.wav", "origin": "recorded"},
            content=body,
            headers={"content-type": "audio/wav"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        reference = response.json()
        self.assertTrue(reference["id"].startswith("aud_"))
        self.assertEqual(reference["kind"], "audio")
        self.assertTrue(reference["path"].startswith("assets/aud_"))
        self.assertTrue(reference["path"].endswith(".wav"))
        metadata = reference["metadata"]
        self.assertEqual(metadata["original_name"], "take-01.wav")
        self.assertEqual(metadata["origin"], "recorded")
        self.assertEqual(metadata["role"], "prepared-speech")
        self.assertEqual(metadata["duration_us"], 2_750_000)
        self.assertEqual(metadata["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(metadata["sample_rate"], 48000)
        self.assertEqual(metadata["channels"], 1)
        self.assertNotIn(str(self.store.root), str(reference))

        project = self.store.load_project(self.project_id)
        stored = next(item for item in project.artifacts if item.id == reference["id"])
        stored_path = self.store.project_directory(self.project_id) / stored.path
        self.assertEqual(stored_path.read_bytes(), body)

        metadata_response = self.client.get(
            f"/api/uv/projects/{self.project_id}/prepared-audio/{reference['id']}"
        )
        self.assertEqual(metadata_response.status_code, 200, metadata_response.text)
        self.assertEqual(metadata_response.json(), reference)

        streamed = self.client.get(
            f"/api/uv/projects/{self.project_id}/prepared-audio/{reference['id']}/media",
            headers={"range": "bytes=5-12"},
        )
        self.assertEqual(streamed.status_code, 206, streamed.text)
        self.assertEqual(streamed.content, body[5:13])
        self.assertEqual(streamed.headers["content-range"], f"bytes 5-12/{len(body)}")

    def test_video_containing_upload_is_rejected_and_file_is_cleaned(self) -> None:
        def video_probe(_store, _project_id, relative_path):
            return {
                "path": relative_path,
                "duration_us": 2_000_000,
                "has_video": True,
                "has_audio": True,
                "streams": [],
            }

        app.dependency_overrides[get_prepared_audio_probe] = lambda: video_probe
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/prepared-audio",
            params={"filename": "not-a-speech-take.mp4"},
            content=b"video-and-audio",
            headers={"content-type": "video/mp4"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        project = self.store.load_project(self.project_id)
        self.assertEqual(project.artifacts, ())
        assets = list((self.store.project_directory(self.project_id) / "assets").iterdir())
        self.assertEqual(assets, [])

    def test_oversized_declared_upload_is_rejected_before_allocation(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/prepared-audio",
            params={"filename": "huge.wav"},
            content=b"x",
            headers={
                "content-type": "audio/wav",
                "content-length": str(MAX_PREPARED_AUDIO_UPLOAD_BYTES + 1),
            },
        )
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(self.store.load_project(self.project_id).artifacts, ())

    def test_unknown_audio_id_does_not_fall_back_to_project_path_lookup(self) -> None:
        response = self.client.get(
            f"/api/uv/projects/{self.project_id}/prepared-audio/assets%2Fanything.wav/media"
        )
        self.assertIn(response.status_code, (404, 422))


if __name__ == "__main__":
    unittest.main()
