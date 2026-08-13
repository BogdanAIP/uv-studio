from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise AssertionError(f"required real-media tool is missing: {name}")
    return path


def _ffmpeg(*args: str) -> None:
    completed = subprocess.run(
        [_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
        shell=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)


def _probe(path: Path) -> dict:
    completed = subprocess.run(
        [
            _tool("ffprobe"),
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
        shell=False,
    )
    return json.loads(completed.stdout)


class BrowserPreviewRealMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Browser preview")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.master = self.project_dir / "artifacts" / "master.mkv"
        _ffmpeg(
            "-f",
            "lavfi",
            "-i",
            "testsrc2=s=160x90:r=30:d=2",
            "-map",
            "0:v:0",
            "-c:v",
            "ffv1",
            "-level",
            "3",
            "-pix_fmt",
            "yuv420p",
            str(self.master),
        )
        self.master_ref = ProjectReference(
            id="art_master",
            kind="video",
            path="artifacts/master.mkv",
            metadata={
                "lifecycle": "render",
                "source_path": "sources/source.mkv",
                "edit_ids": ["edit_one"],
            },
        )
        self.store.update_project(
            self.project.project_id,
            artifacts=(self.master_ref,),
        )
        app.dependency_overrides[get_project_store] = lambda: self.store
        get_capability_registry.cache_clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        get_capability_registry.cache_clear()
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_master_artifact_projects_to_seekable_h264_mp4_without_reediting(self) -> None:
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/video.preview_artifact/execute",
            json={"input": {"artifact_id": self.master_ref.id}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["result"]
        self.assertEqual(result["capability_id"], "video.preview_artifact")
        artifact = result["artifact"]
        self.assertEqual(artifact["metadata"]["lifecycle"], "browser_preview")
        self.assertEqual(artifact["metadata"]["source_artifact_id"], self.master_ref.id)
        self.assertEqual(artifact["metadata"]["edit_ids"], ["edit_one"])
        preview = self.project_dir / artifact["path"]
        self.assertTrue(preview.is_file())
        self.assertEqual(preview.suffix, ".mp4")

        probe = _probe(preview)
        format_names = str(probe.get("format", {}).get("format_name", "")).split(",")
        self.assertIn("mp4", format_names)
        video = next(
            stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"
        )
        self.assertEqual(video.get("codec_name"), "h264")
        self.assertEqual(video.get("pix_fmt"), "yuv420p")

        media = self.client.get(
            f"/api/uv/projects/{self.project.project_id}/artifacts/{artifact['id']}/media",
            headers={"Range": "bytes=0-99"},
        )
        self.assertEqual(media.status_code, 206, media.text)
        self.assertEqual(media.headers.get("content-type"), "video/mp4")
        self.assertTrue(media.headers.get("content-range", "").startswith("bytes 0-99/"))
        self.assertEqual(len(media.content), 100)


if __name__ == "__main__":
    unittest.main()
