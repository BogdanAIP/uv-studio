from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.dubbing import DubbingStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class DubbingCommandsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"title": "Dubbing Project"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]

        media_store = ProjectSourceMediaStore(self.store)
        allocation = media_store.allocate(self.project_id, "dialogue-source.mp4")
        allocation.absolute_path.write_bytes(b"registered-dialogue-video")
        project = media_store.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "dialogue-source.mp4",
                "content_type": "video/mp4",
                "size_bytes": len(b"registered-dialogue-video"),
                "sha256": "1" * 64,
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

    def _import_transcript(self) -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en-US",
                "start_us": 1_000_000,
                "end_us": 8_000_000,
                "segments": [
                    {
                        "segment_id": "seg_001",
                        "start_us": 1_000_000,
                        "end_us": 3_000_000,
                        "text": "Hello there",
                        "speaker_label": "Speaker 1",
                    },
                    {
                        "segment_id": "seg_002",
                        "start_us": 4_000_000,
                        "end_us": 7_500_000,
                        "text": "This is the second line",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_import_transcript_uses_source_id_and_server_owned_revision_binding(self) -> None:
        result = self._import_transcript()
        self.assertEqual(result["command"], "import_dubbing_transcript")
        self.assertTrue(result["dubbing_id"].startswith("dub_"))
        transcript = result["payload"]["transcript"]
        self.assertEqual(transcript["source_id"], self.source.id)
        self.assertEqual(transcript["source_sha256"], "1" * 64)
        self.assertEqual(transcript["language"], "en-us")
        self.assertEqual(transcript["origin"], "imported")
        self.assertEqual(len(result["payload"]["transcript_sha256"]), 64)

        persisted = DubbingStore(self.store).validate_project(self.project_id)
        self.assertEqual(persisted.transcripts[0].to_dict(), transcript)

        state = self.client.get(f"/api/uv/projects/{self.project_id}/editor/state")
        self.assertEqual(state.status_code, 200, state.text)
        dubbing = state.json()["dubbing"]
        self.assertEqual([item["dubbing_id"] for item in dubbing["transcripts"]], [result["dubbing_id"]])
        self.assertEqual(dubbing["translations"], [])

    def test_accept_asr_transcript_requires_explicit_command_and_rebinds_source_revision(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_asr_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 2_000_000,
                "end_us": 6_000_000,
                "segments": [
                    {
                        "segment_id": "seg_000001",
                        "start_us": 2_000_000,
                        "end_us": 3_250_000,
                        "text": "Reviewed and corrected ASR text",
                        "confidence": 0.91,
                    },
                    {
                        "segment_id": "seg_000002",
                        "start_us": 3_500_000,
                        "end_us": 5_500_000,
                        "text": "Second reviewed segment",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result["command"], "accept_asr_transcript")
        transcript = result["payload"]["transcript"]
        self.assertEqual(transcript["origin"], "asr")
        self.assertEqual(transcript["source_id"], self.source.id)
        self.assertEqual(transcript["source_sha256"], "1" * 64)
        self.assertEqual(transcript["segments"][0]["text"], "Reviewed and corrected ASR text")
        self.assertEqual(len(result["payload"]["transcript_sha256"]), 64)

        persisted = DubbingStore(self.store).validate_project(self.project_id)
        self.assertEqual(persisted.get_transcript(result["dubbing_id"]).origin, "asr")

    def test_translation_command_binds_exact_current_transcript_revision(self) -> None:
        imported = self._import_transcript()
        dubbing_id = imported["dubbing_id"]
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "upsert_dubbing_translation",
                "dubbing_id": dubbing_id,
                "target_language": "ru",
                "segments": [
                    {"segment_id": "seg_001", "text": "Привет"},
                    {"segment_id": "seg_002", "text": "Это вторая строка"},
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result["command"], "upsert_dubbing_translation")
        translation = result["payload"]["translation"]
        self.assertTrue(translation["translation_id"].startswith("translation_"))
        self.assertEqual(
            translation["transcript_sha256"],
            imported["payload"]["transcript_sha256"],
        )
        self.assertEqual(translation["target_language"], "ru")

        state = self.client.get(f"/api/uv/projects/{self.project_id}/editor/state")
        self.assertEqual(state.status_code, 200, state.text)
        self.assertEqual(
            state.json()["dubbing"]["translations"][0]["translation_id"],
            translation["translation_id"],
        )

    def test_translation_rejects_missing_segments_and_unknown_transcript(self) -> None:
        imported = self._import_transcript()
        incomplete = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "upsert_dubbing_translation",
                "dubbing_id": imported["dubbing_id"],
                "target_language": "ru",
                "segments": [{"segment_id": "seg_001", "text": "Привет"}],
            },
        )
        self.assertEqual(incomplete.status_code, 422, incomplete.text)

        missing = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "upsert_dubbing_translation",
                "dubbing_id": "dub_missing",
                "target_language": "ru",
                "segments": [{"segment_id": "seg_001", "text": "Привет"}],
            },
        )
        self.assertEqual(missing.status_code, 404, missing.text)

    def test_transcript_commands_reject_client_controlled_source_revision_and_raw_path(self) -> None:
        for command in ("import_dubbing_transcript", "accept_asr_transcript"):
            with self.subTest(command=command):
                bypass = self.client.post(
                    f"/api/uv/projects/{self.project_id}/editor/commands",
                    json={
                        "command": command,
                        "source_id": self.source.id,
                        "source_path": "sources/attacker.wav",
                        "source_sha256": "f" * 64,
                        "offer_id": "remote.magic",
                        "language": "en",
                        "start_us": 0,
                        "end_us": 2_000_000,
                        "segments": [
                            {
                                "segment_id": "seg_001",
                                "start_us": 0,
                                "end_us": 1_000_000,
                                "text": "Bypass",
                            }
                        ],
                    },
                )
                self.assertEqual(bypass.status_code, 422, bypass.text)
        self.assertEqual(DubbingStore(self.store).load(self.project_id).transcripts, ())

    def test_import_rejects_range_outside_registered_source_duration(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 11_000_000,
                "end_us": 13_000_000,
                "segments": [
                    {
                        "segment_id": "seg_001",
                        "start_us": 11_000_000,
                        "end_us": 12_500_000,
                        "text": "Outside",
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(DubbingStore(self.store).load(self.project_id).transcripts, ())


if __name__ == "__main__":
    unittest.main()
