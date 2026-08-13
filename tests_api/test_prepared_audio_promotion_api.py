from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.prepared_audio import get_prepared_audio_probe
from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class PreparedAudioPromotionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Promote TTS")
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_prepared_audio_probe] = lambda: self._probe
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _probe(store, project_id, relative_path):
        return {
            "path": relative_path,
            "has_audio": True,
            "has_video": False,
            "duration_us": 1_750_000,
            "format_name": "mp3",
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "mp3",
                    "sample_rate": "48000",
                    "channels": 2,
                    "channel_layout": "stereo",
                    "sample_fmt": "fltp",
                }
            ],
        }

    def _add_artifact(self, *, kind: str = "audio") -> tuple[ProjectReference, bytes]:
        body = b"project-owned-generated-audio-bytes"
        path = self.store.resolve_project_file(
            self.project.project_id,
            "artifacts/art_tts.mp3",
            must_exist=False,
            allowed_roots=("artifacts",),
        )
        path.write_bytes(body)
        artifact = ProjectReference(
            id="art_tts",
            kind=kind,
            path="artifacts/art_tts.mp3",
            metadata={
                "capability_id": "speech.synthesize",
                "offer_id": "native_videoclaw.edge_tts",
                "content_type": "audio/mpeg",
            },
        )
        current = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*current.artifacts, artifact),
        )
        return artifact, body

    def test_audio_artifact_is_copied_rehashed_reprobed_and_registered_as_tts_prepared_speech(self) -> None:
        source, body = self._add_artifact()
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/prepared-audio/from-artifact/{source.id}"
        )
        self.assertEqual(response.status_code, 201, response.text)
        prepared = response.json()
        self.assertTrue(prepared["id"].startswith("aud_"))
        self.assertEqual(prepared["kind"], "audio")
        self.assertTrue(prepared["path"].startswith("assets/"))
        self.assertEqual(prepared["metadata"]["role"], "prepared-speech")
        self.assertEqual(prepared["metadata"]["origin"], "tts")
        self.assertEqual(prepared["metadata"]["duration_us"], 1_750_000)
        self.assertEqual(prepared["metadata"]["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(prepared["metadata"]["promoted_from_artifact_id"], source.id)
        self.assertNotEqual(prepared["path"], source.path)

        copied = self.store.resolve_project_file(
            self.project.project_id,
            prepared["path"],
            must_exist=True,
            allowed_roots=("assets",),
        )
        self.assertEqual(copied.read_bytes(), body)

    def test_missing_non_audio_and_client_path_bypass_fail_closed(self) -> None:
        missing = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/prepared-audio/from-artifact/art_missing"
        )
        self.assertEqual(missing.status_code, 404, missing.text)

        wrong, _body = self._add_artifact(kind="video")
        wrong_kind = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/prepared-audio/from-artifact/{wrong.id}"
        )
        self.assertEqual(wrong_kind.status_code, 422, wrong_kind.text)

        bypass = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/prepared-audio/from-artifact/{wrong.id}",
            json={"path": "C:/outside/voice.mp3", "sha256": "f" * 64},
        )
        self.assertEqual(bypass.status_code, 422, bypass.text)


if __name__ == "__main__":
    unittest.main()
