from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects import AcceptedRangeEdit, ProjectStore, RangeEditStateStore
from uv_studio.server import app


class EditStateApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Edit API")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        (self.project_dir / "artifacts" / "replacement-a.mkv").write_bytes(b"a")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/edits"

    def _command_url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/editor/commands"

    def _accept_internal_edit(self) -> None:
        RangeEditStateStore(self.store).accept(
            self.project.project_id,
            AcceptedRangeEdit(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                replacement_path="artifacts/replacement-a.mkv",
            ),
        )

    def test_direct_http_edit_creation_or_deletion_is_not_a_public_mutation_path(self) -> None:
        created = self.client.post(
            self._url(),
            json={
                "edit_id": "edit_1",
                "source_path": "sources/source.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "replacement_path": "artifacts/replacement-a.mkv",
            },
        )
        self.assertEqual(created.status_code, 405, created.text)

        self._accept_internal_edit()
        deleted = self.client.delete(f"{self._url()}/edit_1")
        self.assertEqual(deleted.status_code, 405, deleted.text)

        fetched = self.client.get(self._url())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual([item["edit_id"] for item in fetched.json()["edits"]], ["edit_1"])

    def test_read_and_remove_use_shared_editor_command_boundary(self) -> None:
        self._accept_internal_edit()

        fetched = self.client.get(self._url())
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["edits"][0]["edit_id"], "edit_1")

        removed = self.client.post(
            self._command_url(),
            json={"command": "remove_accepted_edit", "edit_id": "edit_1"},
        )
        self.assertEqual(removed.status_code, 201, removed.text)
        self.assertEqual(removed.json()["command"], "remove_accepted_edit")
        self.assertEqual(removed.json()["edit_id"], "edit_1")
        self.assertEqual(removed.json()["state"]["edits"], [])

        fetched_after = self.client.get(self._url())
        self.assertEqual(fetched_after.status_code, 200, fetched_after.text)
        self.assertEqual(fetched_after.json()["edits"], [])

    def test_empty_state_and_missing_project_or_edit(self) -> None:
        empty = self.client.get(self._url())
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json()["edits"], [])

        missing_project = self.client.get("/api/uv/projects/prj_missing/edits")
        self.assertEqual(missing_project.status_code, 404, missing_project.text)

        missing_project_command = self.client.post(
            "/api/uv/projects/prj_missing/editor/commands",
            json={"command": "remove_accepted_edit", "edit_id": "edit_1"},
        )
        self.assertEqual(missing_project_command.status_code, 404, missing_project_command.text)

        missing_edit = self.client.post(
            self._command_url(),
            json={"command": "remove_accepted_edit", "edit_id": "missing_edit"},
        )
        self.assertEqual(missing_edit.status_code, 404, missing_edit.text)


if __name__ == "__main__":
    unittest.main()
