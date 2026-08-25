from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class ArtifactDownloadApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.project = self.store.create_project(recipe_id="general_video", title="Artifact download")
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def _register(self, reference: ProjectReference, body: bytes) -> None:
        path = self.store.resolve_project_file(
            self.project.project_id,
            reference.path,
            must_exist=False,
            allowed_roots=(reference.path.split("/", 1)[0],),
        )
        path.write_bytes(body)
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, reference),
        )

    def test_registered_subtitle_artifact_download_is_project_scoped_and_attachment_bounded(self) -> None:
        body = b"WEBVTT\n\nseg_1\n00:00:00.000 --> 00:00:01.000\nHello\n"
        reference = ProjectReference(
            id="sub_test",
            kind="subtitle",
            path="artifacts/sub_test.vtt",
            metadata={
                "content_type": "text/vtt; charset=utf-8",
                "original_name": "dialogue.en.vtt",
            },
        )
        self._register(reference, body)

        response = self.client.get(
            f"/api/uv/projects/{self.project.project_id}/artifacts/{reference.id}/file"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, body)
        self.assertTrue(response.headers["content-type"].lower().startswith("text/vtt"))
        disposition = response.headers.get("content-disposition", "")
        self.assertIn("attachment", disposition.lower())
        self.assertIn("dialogue.en.vtt", disposition)

    def test_untrusted_download_metadata_falls_back_to_registered_artifact_filename_and_type(self) -> None:
        body = b"WEBVTT\n"
        reference = ProjectReference(
            id="sub_metadata",
            kind="subtitle",
            path="artifacts/sub_metadata.vtt",
            metadata={
                "content_type": "text/vtt\r\nx-injected: yes",
                "original_name": "bad\r\nname.vtt",
            },
        )
        self._register(reference, body)

        response = self.client.get(
            f"/api/uv/projects/{self.project.project_id}/artifacts/{reference.id}/file"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, body)
        self.assertTrue(response.headers["content-type"].lower().startswith("text/vtt"))
        disposition = response.headers.get("content-disposition", "")
        self.assertIn("sub_metadata.vtt", disposition)
        self.assertNotIn("bad", disposition)
        self.assertNotIn("x-injected", str(response.headers).lower())

    def test_unknown_artifact_and_registered_non_artifacts_path_fail_closed(self) -> None:
        missing = self.client.get(
            f"/api/uv/projects/{self.project.project_id}/artifacts/sub_missing/file"
        )
        self.assertEqual(missing.status_code, 404, missing.text)

        bad = ProjectReference(
            id="sub_bad_root",
            kind="subtitle",
            path="sources/sub_bad_root.vtt",
            metadata={"content_type": "text/vtt"},
        )
        self._register(bad, b"WEBVTT\n")
        rejected = self.client.get(
            f"/api/uv/projects/{self.project.project_id}/artifacts/{bad.id}/file"
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertIn("artifacts/", rejected.text)


if __name__ == "__main__":
    unittest.main()
