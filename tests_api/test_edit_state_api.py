from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects import EDIT_STATE_PATH, ProjectStore
from uv_studio.server import app


class EditStateApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Edit API")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        (self.project_dir / "artifacts" / "replacement-a.mkv").write_bytes(b"a")
        (self.project_dir / "artifacts" / "replacement-b.mkv").write_bytes(b"b")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/edits"

    def test_accept_read_and_remove_edit_without_render_artifact(self) -> None:
        before = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        accepted = self.client.post(
            self._url(),
            json={
                "edit_id": "edit_1",
                "source_path": "sources/source.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "replacement_path": "artifacts/replacement-a.mkv",
            },
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        self.assertEqual(accepted.json()["edits"][0]["edit_id"], "edit_1")
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            before,
        )
        self.assertTrue((self.project_dir / EDIT_STATE_PATH).is_file())

        fetched = self.client.get(self._url())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json(), accepted.json())

        removed = self.client.delete(f"{self._url()}/edit_1")
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(removed.json()["edits"], [])

    def test_overlap_and_missing_replacement_are_422(self) -> None:
        first = self.client.post(
            self._url(),
            json={
                "edit_id": "edit_1",
                "source_path": "sources/source.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "replacement_path": "artifacts/replacement-a.mkv",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)

        overlap = self.client.post(
            self._url(),
            json={
                "edit_id": "edit_2",
                "source_path": "sources/source.mkv",
                "start_us": 1_500_000,
                "end_us": 2_500_000,
                "replacement_path": "artifacts/replacement-b.mkv",
            },
        )
        self.assertEqual(overlap.status_code, 422, overlap.text)

        missing = self.client.post(
            self._url(),
            json={
                "edit_id": "edit_3",
                "source_path": "sources/source.mkv",
                "start_us": 3_000_000,
                "end_us": 4_000_000,
                "replacement_path": "artifacts/missing.mkv",
            },
        )
        self.assertEqual(missing.status_code, 422, missing.text)

    def test_missing_project_and_missing_edit_are_404(self) -> None:
        missing_project = self.client.get("/api/uv/projects/prj_missing/edits")
        self.assertEqual(missing_project.status_code, 404, missing_project.text)

        missing_edit = self.client.delete(f"{self._url()}/missing_edit")
        self.assertEqual(missing_edit.status_code, 404, missing_edit.text)

    def test_request_rejects_unknown_fields_and_invalid_interval(self) -> None:
        response = self.client.post(
            self._url(),
            json={
                "edit_id": "edit_bad",
                "source_path": "sources/source.mkv",
                "start_us": 2_000_000,
                "end_us": 1_000_000,
                "replacement_path": "artifacts/replacement-a.mkv",
                "provider": "should-not-exist",
            },
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
