from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class EditorEngineProjectionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(recipe_id="general_video", title="MLT public projection")
        self.project_dir = self.store.project_directory(self.project.project_id)
        source_path = self.project_dir / "sources" / "clip.mp4"
        source_path.write_bytes(b"project-owned fixture")
        self.source = ProjectReference(
            id="src_clip",
            kind="video",
            path="sources/clip.mp4",
            metadata={
                "duration_us": 2_000_000,
                "width": 320,
                "height": 180,
                "avg_frame_rate": "30/1",
            },
        )
        self.store.update_project(self.project.project_id, sources=(self.source,))
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_editor_state_exposes_bounded_mlt_summary_without_xml_or_host_paths(self) -> None:
        response = self.client.get(f"/api/uv/projects/{self.project.project_id}/editor/state")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        engine = payload["engine"]
        self.assertEqual(engine["adapter_id"], "mlt")
        self.assertIsInstance(engine["runtime_available"], bool)
        self.assertEqual(len(engine["timelines"]), 1)
        timeline = engine["timelines"][0]
        self.assertEqual(timeline["status"], "ready")
        self.assertEqual(timeline["source_path"], self.source.path)
        self.assertEqual(timeline["frame_rate"], "30/1")
        self.assertEqual(timeline["segment_count"], 1)
        self.assertEqual(timeline["segments"][0]["project_path"], self.source.path)

        serialized = json.dumps(engine, sort_keys=True)
        self.assertNotIn("xml_text", serialized)
        self.assertNotIn("<mlt", serialized)
        self.assertNotIn(str(self.project_dir.resolve()), serialized)
        self.assertNotIn(str((self.project_dir / self.source.path).resolve()), serialized)


if __name__ == "__main__":
    unittest.main()
