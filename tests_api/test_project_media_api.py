from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.project_media import get_source_media_probe
from uv_studio.api.projects import get_project_store
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


class ProjectMediaApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_source_media_probe] = lambda: self._probe_video
        self.client = TestClient(app)
        created = self.client.post("/api/uv/projects", json={"title": "Media Project"})
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _probe_video(store: ProjectStore, project_id: str, relative_path: str) -> dict[str, object]:
        path = store.resolve_project_file(
            project_id,
            relative_path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        return {
            "path": relative_path,
            "duration_us": 7_500_000,
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "size_bytes": path.stat().st_size,
            "has_video": True,
            "has_audio": True,
            "video": {
                "codec": "h264",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30/1",
                "duration_us": 7_500_000,
            },
            "streams": [{"codec_type": "video", "host_path": "must-not-persist"}],
        }

    def test_upload_registers_only_portable_metadata_and_delivers_ranges(self) -> None:
        body = b"0123456789abcdefghijklmnopqrstuvwxyz"
        upload = self.client.post(
            f"/api/uv/projects/{self.project_id}/sources",
            params={"filename": r"C:\Users\someone\Example Clip.MP4"},
            content=body,
            headers={"Content-Type": "video/mp4"},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        source = upload.json()
        self.assertTrue(source["id"].startswith("src_"))
        self.assertEqual(source["kind"], "video")
        self.assertTrue(source["path"].startswith("sources/src_"))
        self.assertTrue(source["path"].endswith(".mp4"))
        metadata = source["metadata"]
        self.assertEqual(metadata["original_name"], "Example Clip.MP4")
        self.assertEqual(metadata["duration_us"], 7_500_000)
        self.assertEqual(metadata["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(metadata["size_bytes"], len(body))
        self.assertEqual(metadata["width"], 1920)
        self.assertNotIn("streams", metadata)
        self.assertNotIn("path", metadata)
        self.assertNotIn("host_path", str(metadata))

        project = self.store.load_project(self.project_id)
        self.assertEqual(len(project.sources), 1)
        stored_path = self.store.resolve_project_file(
            self.project_id,
            project.sources[0].path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        self.assertEqual(stored_path.read_bytes(), body)

        detail = self.client.get(
            f"/api/uv/projects/{self.project_id}/sources/{source['id']}"
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json(), source)

        whole = self.client.get(
            f"/api/uv/projects/{self.project_id}/sources/{source['id']}/media"
        )
        self.assertEqual(whole.status_code, 200, whole.text)
        self.assertEqual(whole.content, body)
        self.assertEqual(whole.headers["content-type"], "video/mp4")
        self.assertEqual(whole.headers.get("accept-ranges"), "bytes")

        ranged = self.client.get(
            f"/api/uv/projects/{self.project_id}/sources/{source['id']}/media",
            headers={"Range": "bytes=2-5"},
        )
        self.assertEqual(ranged.status_code, 206, ranged.text)
        self.assertEqual(ranged.content, body[2:6])
        self.assertEqual(ranged.headers.get("content-range"), f"bytes 2-5/{len(body)}")

    def test_empty_or_non_video_upload_is_not_registered(self) -> None:
        empty = self.client.post(
            f"/api/uv/projects/{self.project_id}/sources",
            params={"filename": "empty.mp4"},
            content=b"",
            headers={"Content-Type": "video/mp4"},
        )
        self.assertEqual(empty.status_code, 400, empty.text)
        self.assertEqual(self.store.load_project(self.project_id).sources, ())
        self.assertEqual(list(self.store.project_directory(self.project_id).joinpath("sources").iterdir()), [])

        def non_video_probe(store: ProjectStore, project_id: str, relative_path: str) -> dict[str, object]:
            return {
                "path": relative_path,
                "duration_us": 1_000_000,
                "has_video": False,
                "has_audio": True,
                "video": None,
            }

        app.dependency_overrides[get_source_media_probe] = lambda: non_video_probe
        rejected = self.client.post(
            f"/api/uv/projects/{self.project_id}/sources",
            params={"filename": "audio-disguised.mp4"},
            content=b"not-really-video",
            headers={"Content-Type": "video/mp4"},
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(self.store.load_project(self.project_id).sources, ())
        self.assertEqual(list(self.store.project_directory(self.project_id).joinpath("sources").iterdir()), [])

    def test_unknown_project_and_source_are_404(self) -> None:
        missing_project = self.client.post(
            "/api/uv/projects/prj_missing/sources",
            params={"filename": "clip.mp4"},
            content=b"video",
            headers={"Content-Type": "video/mp4"},
        )
        self.assertEqual(missing_project.status_code, 404, missing_project.text)

        missing_source = self.client.get(
            f"/api/uv/projects/{self.project_id}/sources/src_missing/media"
        )
        self.assertEqual(missing_source.status_code, 404, missing_source.text)

    def test_oversized_content_length_fails_before_creating_source(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/sources",
            params={"filename": "huge.mp4"},
            content=b"small",
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(100 * 1024**3 + 1),
            },
        )
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(self.store.load_project(self.project_id).sources, ())


if __name__ == "__main__":
    unittest.main()
