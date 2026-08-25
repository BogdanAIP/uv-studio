from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.project_common import get_project_store
from uv_studio.api.project_media import get_source_media_probe
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class ProjectTransactionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post(
            "/api/uv/projects/studio",
            json={"title": "Undo Studio", "direction_id": "free_project"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _history(self) -> dict:
        response = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/history"
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_timeline_command_uses_shared_transaction_and_http_undo_redo(self) -> None:
        self.assertEqual(
            self._history(),
            {
                "schema_version": 1,
                "cursor": 0,
                "can_undo": False,
                "can_redo": False,
                "current_transaction_id": None,
                "entries": [],
            },
        )

        created = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/timeline/commands",
            json={"command": "create_track", "kind": "video", "track_id": "trk_undo"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        transaction_id = created.json()["transaction_id"]
        self.assertTrue(transaction_id.startswith("tx_"))

        history = self._history()
        self.assertEqual(history["cursor"], 1)
        self.assertTrue(history["can_undo"])
        self.assertFalse(history["can_redo"])
        self.assertEqual(history["current_transaction_id"], transaction_id)
        self.assertEqual(history["entries"][0]["command"], "timeline.create_track")
        self.assertEqual(history["entries"][0]["changed_paths"], ["timeline/main.json"])

        undone = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/history/undo"
        )
        self.assertEqual(undone.status_code, 200, undone.text)
        self.assertEqual(undone.json()["transaction_id"], transaction_id)
        self.assertEqual(undone.json()["operation"], "undo")
        self.assertEqual(undone.json()["history"]["cursor"], 0)
        timeline = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/timeline"
        )
        self.assertEqual(timeline.status_code, 200, timeline.text)
        self.assertEqual(timeline.json()["tracks"], [])

        redone = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/history/redo"
        )
        self.assertEqual(redone.status_code, 200, redone.text)
        self.assertEqual(redone.json()["transaction_id"], transaction_id)
        self.assertEqual(redone.json()["operation"], "redo")
        timeline = self.client.get(
            f"/api/uv/projects/{self.project_id}/studio/timeline"
        )
        self.assertEqual(timeline.status_code, 200, timeline.text)
        self.assertEqual(timeline.json()["tracks"][0]["track_id"], "trk_undo")

    def test_empty_history_returns_conflict_for_undo_and_redo(self) -> None:
        undo = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/history/undo"
        )
        self.assertEqual(undo.status_code, 409, undo.text)
        self.assertIn("nothing to undo", undo.json()["detail"])

        redo = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/history/redo"
        )
        self.assertEqual(redo.status_code, 409, redo.text)
        self.assertIn("nothing to redo", redo.json()["detail"])

    def test_media_registration_is_a_project_transaction(self) -> None:
        body = b"transactional-source"

        def probe(store: ProjectStore, project_id: str, relative_path: str) -> dict:
            return {
                "path": relative_path,
                "duration_us": 2_000_000,
                "format_name": "mov,mp4",
                "size_bytes": len(body),
                "has_video": True,
                "has_audio": False,
                "video": {
                    "codec": "h264",
                    "width": 640,
                    "height": 360,
                    "avg_frame_rate": "25/1",
                    "duration_us": 2_000_000,
                },
            }

        app.dependency_overrides[get_source_media_probe] = lambda: probe
        uploaded = self.client.post(
            f"/api/uv/projects/{self.project_id}/sources",
            params={"filename": "source.mp4"},
            content=body,
            headers={"Content-Type": "video/mp4"},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        source = uploaded.json()
        self.assertEqual(source["metadata"]["sha256"], hashlib.sha256(body).hexdigest())

        history = self._history()
        self.assertEqual(history["entries"][0]["command"], "register_video_source")
        self.assertEqual(history["entries"][0]["changed_paths"], ["project.json"])

        undone = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/history/undo"
        )
        self.assertEqual(undone.status_code, 200, undone.text)
        self.assertEqual(self.store.load_project(self.project_id).sources, ())

        redone = self.client.post(
            f"/api/uv/projects/{self.project_id}/studio/history/redo"
        )
        self.assertEqual(redone.status_code, 200, redone.text)
        restored = self.store.load_project(self.project_id).sources
        self.assertEqual([item.id for item in restored], [source["id"]])


if __name__ == "__main__":
    unittest.main()
