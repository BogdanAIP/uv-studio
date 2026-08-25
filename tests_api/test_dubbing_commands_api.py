from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.dubbing import DubbingStore
from uv_studio.projects.prepared_audio import ProjectPreparedAudioStore
from uv_studio.projects.prepared_speech import PreparedSpeechStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class DubbingCommandsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"recipe_id": "general_video", "title": "Dubbing Project"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project_id, "dialogue-source.mp4")
        body = b"registered-dialogue-video"
        allocation.absolute_path.write_bytes(body)
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "dialogue-source.mp4",
                "content_type": "video/mp4",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 12_000_000,
                "has_audio": True,
                "width": 1280,
                "height": 720,
            },
        )
        self.source = project.sources[0]

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @property
    def command_url(self) -> str:
        return f"/api/uv/projects/{self.project_id}/editor/commands"

    def _import_transcript(self) -> dict:
        response = self.client.post(
            self.command_url,
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en-US",
                "start_us": 1_000_000,
                "end_us": 8_000_000,
                "segments": [
                    {"segment_id": "seg_001", "start_us": 1_000_000, "end_us": 3_000_000, "text": "Hello there"},
                    {"segment_id": "seg_002", "start_us": 4_000_000, "end_us": 7_500_000, "text": "Second line"},
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _translation(self, dubbing_id: str, *, translation_id: str | None = None, language: str = "ru") -> dict:
        payload = {
            "command": "upsert_dubbing_translation",
            "dubbing_id": dubbing_id,
            "target_language": language,
            "segments": [
                {"segment_id": "seg_001", "text": "Привет" if language == "ru" else "Hallo"},
                {"segment_id": "seg_002", "text": "Вторая строка" if language == "ru" else "Zweite Zeile"},
            ],
        }
        if translation_id is not None:
            payload["translation_id"] = translation_id
        response = self.client.post(self.command_url, json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["payload"]["translation"]

    def _audio(self, *, origin: str = "recorded"):
        media = ProjectPreparedAudioStore(self.store)
        allocation = media.allocate(self.project_id, "voice.wav")
        body = b"prepared-speech-audio"
        allocation.absolute_path.write_bytes(body)
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "voice.wav",
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 1_850_000,
                "has_audio": True,
                "has_video": False,
                "origin": origin,
            },
        )
        return next(item for item in project.artifacts if item.id == allocation.audio_id)

    def test_import_and_asr_bind_current_source_bytes(self) -> None:
        imported = self._import_transcript()
        transcript = imported["payload"]["transcript"]
        self.assertEqual(transcript["source_sha256"], self.source.metadata["sha256"])
        self.assertEqual(transcript["origin"], "imported")
        asr = self.client.post(
            self.command_url,
            json={
                "command": "accept_asr_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
                "segments": [{"segment_id": "seg_asr", "start_us": 2_000_000, "end_us": 4_000_000, "text": "Reviewed ASR"}],
            },
        )
        self.assertEqual(asr.status_code, 201, asr.text)
        self.assertEqual(asr.json()["payload"]["transcript"]["source_sha256"], self.source.metadata["sha256"])

    def test_translation_language_change_creates_new_identity(self) -> None:
        imported = self._import_transcript()
        first = self._translation(imported["dubbing_id"])
        second = self._translation(imported["dubbing_id"], translation_id=first["translation_id"], language="de")
        self.assertNotEqual(second["translation_id"], first["translation_id"])
        state = DubbingStore(self.store).validate_project(self.project_id)
        self.assertEqual(state.get_translation(first["translation_id"]).target_language, "ru")
        self.assertEqual(state.get_translation(second["translation_id"]).target_language, "de")

    def test_attach_binds_exact_audio_and_script(self) -> None:
        imported = self._import_transcript()
        audio = self._audio()
        response = self.client.post(
            self.command_url,
            json={"command": "attach_prepared_speech", "dubbing_id": imported["dubbing_id"], "audio_id": audio.id, "segment_id": "seg_001"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        take = response.json()["payload"]["prepared_speech"]
        self.assertEqual(take["script_sha256"], imported["payload"]["transcript_sha256"])
        self.assertEqual(take["audio_sha256"], audio.metadata["sha256"])
        self.assertEqual(PreparedSpeechStore(self.store).validate_project(self.project_id).get(take["take_id"]).to_dict(), take)

    def test_bound_translation_cannot_change_same_identity(self) -> None:
        imported = self._import_transcript()
        translation = self._translation(imported["dubbing_id"])
        audio = self._audio(origin="imported")
        attached = self.client.post(
            self.command_url,
            json={"command": "attach_prepared_speech", "dubbing_id": imported["dubbing_id"], "translation_id": translation["translation_id"], "audio_id": audio.id},
        )
        self.assertEqual(attached.status_code, 201, attached.text)
        changed = self.client.post(
            self.command_url,
            json={
                "command": "upsert_dubbing_translation",
                "dubbing_id": imported["dubbing_id"],
                "translation_id": translation["translation_id"],
                "target_language": "ru",
                "segments": [{"segment_id": "seg_001", "text": "Изменено"}, {"segment_id": "seg_002", "text": "Вторая строка"}],
            },
        )
        self.assertEqual(changed.status_code, 422, changed.text)

    def test_source_change_after_registration_fails_closed(self) -> None:
        _reference, path = ProjectSourceMediaStore(self.store).resolve(self.project_id, self.source.id)
        path.write_bytes(b"changed-dialogue-video")
        response = self.client.post(
            self.command_url,
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 0,
                "end_us": 1_000_000,
                "segments": [{"segment_id": "seg_changed", "start_us": 0, "end_us": 1_000_000, "text": "Changed"}],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(DubbingStore(self.store).load(self.project_id).transcripts, ())

    def test_invalid_inputs_fail_closed(self) -> None:
        imported = self._import_transcript()
        missing_audio = self.client.post(
            self.command_url,
            json={"command": "attach_prepared_speech", "dubbing_id": imported["dubbing_id"], "audio_id": "aud_missing"},
        )
        self.assertEqual(missing_audio.status_code, 404, missing_audio.text)
        incomplete = self.client.post(
            self.command_url,
            json={"command": "upsert_dubbing_translation", "dubbing_id": imported["dubbing_id"], "target_language": "ru", "segments": [{"segment_id": "seg_001", "text": "Привет"}]},
        )
        self.assertEqual(incomplete.status_code, 422, incomplete.text)
        outside = self.client.post(
            self.command_url,
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 11_000_000,
                "end_us": 13_000_000,
                "segments": [{"segment_id": "seg_out", "start_us": 11_000_000, "end_us": 12_500_000, "text": "Outside"}],
            },
        )
        self.assertEqual(outside.status_code, 422, outside.text)


if __name__ == "__main__":
    unittest.main()
