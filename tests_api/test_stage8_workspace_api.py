from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class Stage8WorkspaceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _project(self, recipe_id: str):
        return self.store.create_project(title=f"Workspace {recipe_id}", recipe_id=recipe_id)

    def _source(self, project_id: str, source_id: str, kind: str, filename: str, body: bytes):
        project_dir = self.store.project_directory(project_id)
        path = project_dir / "sources" / filename
        path.write_bytes(body)
        reference = ProjectReference(
            id=source_id,
            kind=kind,
            path=f"sources/{filename}",
            metadata={
                "original_name": filename,
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            },
        )
        current = self.store.load_project(project_id)
        self.store.update_project(project_id, sources=(*current.sources, reference))
        return reference

    def test_story_workspace_put_get_is_server_bound_to_project_media(self) -> None:
        project = self._project("story_video")
        image = self._source(project.project_id, "src_story", "image", "story.png", b"story")
        response = self.client.put(
            f"/api/uv/projects/{project.project_id}/stage8/workspace",
            json={
                "brief": "История о путешествии",
                "script": "Сцена 1",
                "source_ids": [image.id],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        workspace = response.json()["workspace"]
        self.assertEqual(workspace["recipe_id"], "story_video")
        self.assertEqual(workspace["sources"][0]["source_id"], image.id)
        self.assertEqual(workspace["sources"][0]["role"], "story_image")
        self.assertEqual(workspace["sources"][0]["sha256"], hashlib.sha256(b"story").hexdigest())
        self.assertEqual(len(workspace["revision_sha256"]), 64)

        reopened = self.client.get(f"/api/uv/projects/{project.project_id}/stage8/workspace")
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["workspace"], workspace)

    def test_free_workspace_allows_empty_brief_and_unsupported_recipe_is_rejected(self) -> None:
        free = self._project("free_project")
        response = self.client.put(
            f"/api/uv/projects/{free.project_id}/stage8/workspace",
            json={"brief": "", "script": "", "source_ids": []},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["workspace"]["brief"], "")

        music = self._project("music_video")
        unsupported = self.client.get(f"/api/uv/projects/{music.project_id}/stage8/workspace")
        self.assertEqual(unsupported.status_code, 422, unsupported.text)

    def test_unknown_fields_unknown_source_and_substituted_bytes_fail_closed(self) -> None:
        project = self._project("commercial_product")
        image = self._source(project.project_id, "src_product", "image", "product.png", b"product")
        unknown = self.client.put(
            f"/api/uv/projects/{project.project_id}/stage8/workspace",
            json={"brief": "Реклама", "source_ids": [], "provider": "hidden"},
        )
        self.assertEqual(unknown.status_code, 422, unknown.text)

        missing = self.client.put(
            f"/api/uv/projects/{project.project_id}/stage8/workspace",
            json={"brief": "Реклама", "source_ids": ["src_missing"]},
        )
        self.assertEqual(missing.status_code, 422, missing.text)

        saved = self.client.put(
            f"/api/uv/projects/{project.project_id}/stage8/workspace",
            json={"brief": "Реклама", "source_ids": [image.id]},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        source_path = self.store.resolve_project_file(
            project.project_id,
            image.path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        source_path.write_bytes(b"changed-product")
        stale = self.client.get(f"/api/uv/projects/{project.project_id}/stage8/workspace")
        self.assertEqual(stale.status_code, 422, stale.text)


if __name__ == "__main__":
    unittest.main()
