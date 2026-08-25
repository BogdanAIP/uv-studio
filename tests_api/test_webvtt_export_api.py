from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class WebVTTExportApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"recipe_id": "general_video", "title": "WebVTT export"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]
        self.source = self._source()
        self.dubbing_id = self._transcript()
        self.translation_id = self._translation()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _source(self):
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project_id, "dialogue.mkv")
        body = b"webvtt-source"
        allocation.absolute_path.write_bytes(body)
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "dialogue.mkv",
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
                        "start_us": 1_234_567,
                        "end_us": 2_345_001,
                        "text": "A < B & C",
                    },
                    {
                        "segment_id": "seg_2",
                        "start_us": 3_000_000,
                        "end_us": 4_500_001,
                        "text": "Second line",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["dubbing_id"]

    def _translation(self) -> str:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "upsert_dubbing_translation",
                "dubbing_id": self.dubbing_id,
                "target_language": "ru",
                "segments": [
                    {"segment_id": "seg_1", "text": "А < Б & В"},
                    {"segment_id": "seg_2", "text": "Вторая строка"},
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["payload"]["translation"]["translation_id"]

    def _export(self, input_payload: dict) -> dict:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/subtitle.export_webvtt/execute",
            json={"selection_policy": "local_free_first", "input": input_payload},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]

    def test_translation_export_writes_exact_project_owned_webvtt_and_revision_metadata(self) -> None:
        result = self._export(
            {"dubbing_id": self.dubbing_id, "translation_id": self.translation_id}
        )
        self.assertEqual(result["adapter_id"], "local_webvtt")
        self.assertEqual(result["output"]["format"], "webvtt")
        self.assertEqual(result["output"]["language"], "ru")
        self.assertEqual(result["output"]["cue_count"], 2)
        self.assertEqual(result["output"]["script_kind"], "translation")

        artifact = result["artifact"]
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact["kind"], "subtitle")
        self.assertTrue(artifact["path"].startswith("artifacts/sub_"))
        self.assertEqual(artifact["metadata"]["translation_id"] if "translation_id" in artifact["metadata"] else artifact["metadata"]["script_id"], self.translation_id)
        self.assertEqual(artifact["metadata"]["script_kind"], "translation")
        self.assertEqual(len(artifact["metadata"]["script_sha256"]), 64)
        self.assertEqual(len(artifact["metadata"]["transcript_sha256"]), 64)

        path = self.store.resolve_project_file(
            self.project_id,
            artifact["path"],
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        expected = (
            "WEBVTT\n\n"
            "seg_1\n"
            "00:00:01.234 --> 00:00:02.346\n"
            "А &lt; Б &amp; В\n\n"
            "seg_2\n"
            "00:00:03.000 --> 00:00:04.501\n"
            "Вторая строка\n"
        )
        self.assertEqual(path.read_text(encoding="utf-8"), expected)
        self.assertEqual(
            artifact["metadata"]["sha256"],
            hashlib.sha256(expected.encode("utf-8")).hexdigest(),
        )

        persisted = next(
            item
            for item in self.store.load_project(self.project_id).artifacts
            if item.id == artifact["id"]
        )
        self.assertEqual(persisted.kind, "subtitle")
        self.assertEqual(persisted.metadata["source_id"], self.source.id)

    def test_transcript_export_uses_same_timeline_without_translation(self) -> None:
        result = self._export({"dubbing_id": self.dubbing_id})
        self.assertEqual(result["output"]["script_kind"], "transcript")
        self.assertEqual(result["output"]["language"], "en-us")
        path = self.store.resolve_project_file(
            self.project_id,
            result["output"]["path"],
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn("A &lt; B &amp; C", text)
        self.assertIn("Second line", text)
        self.assertNotIn("Вторая строка", text)

    def test_client_cannot_supply_subtitle_text_timestamps_path_or_provider(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/subtitle.export_webvtt/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {
                    "dubbing_id": self.dubbing_id,
                    "translation_id": self.translation_id,
                    "text": "attacker text",
                    "start_us": 0,
                    "end_us": 999_000_000,
                    "path": "C:/outside/subtitles.vtt",
                    "provider": "remote.magic",
                },
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("unsupported subtitle export fields", response.text)


if __name__ == "__main__":
    unittest.main()
