from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe required")
class Stage8LocalMediaRealMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        created = self.client.post(
            "/api/uv/projects",
            json={"title": "Stage 8 local media", "recipe_id": "photo_to_video"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.project_id = created.json()["project_id"]

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
        completed = subprocess.run(command, capture_output=True, check=False)
        if completed.returncode != 0:
            raise AssertionError(
                f"command failed ({completed.returncode}): {command!r}\n"
                f"{completed.stderr.decode('utf-8', errors='replace')}"
            )
        return completed

    def _image(self, filename: str, color: str):
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project_id, filename)
        self._run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=320x180:d=0.04",
                "-frames:v",
                "1",
                "-update",
                "1",
                str(allocation.absolute_path),
            ]
        )
        body = allocation.absolute_path.read_bytes()
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": filename,
                "content_type": "image/png",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "width": 320,
                "height": 180,
                "has_audio": False,
            },
            media_kind="image",
        )
        return next(item for item in project.sources if item.id == allocation.source_id)

    def _audio(self, filename: str, frequency: int, duration_sec: int):
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project_id, filename)
        self._run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={frequency}:sample_rate=48000:duration={duration_sec}",
                "-c:a",
                "pcm_s16le",
                str(allocation.absolute_path),
            ]
        )
        body = allocation.absolute_path.read_bytes()
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": filename,
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": duration_sec * 1_000_000,
                "has_audio": True,
            },
            media_kind="audio",
        )
        return next(item for item in project.sources if item.id == allocation.source_id)

    def _probe(self, path: Path) -> dict[str, object]:
        completed = self._run(
            [
                shutil.which("ffprobe") or "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ]
        )
        return json.loads(completed.stdout.decode("utf-8"))

    def _rgb_at(self, path: Path, time_sec: float) -> tuple[int, int, int]:
        completed = self._run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{time_sec:.3f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale=1:1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
            ]
        )
        self.assertGreaterEqual(len(completed.stdout), 3)
        return tuple(completed.stdout[:3])  # type: ignore[return-value]

    def test_photo_to_video_preserves_image_order_and_optional_audio(self) -> None:
        red = self._image("red.png", "red")
        blue = self._image("blue.png", "blue")
        audio = self._audio("photo-master.wav", 660, 4)

        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/video.compose_photos/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {
                    "image_source_ids": [red.id, blue.id],
                    "audio_source_id": audio.id,
                    "duration_per_image_us": 2_000_000,
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["result"]
        artifact = result["artifact"]
        self.assertEqual(artifact["metadata"]["lifecycle"], "photo_to_video_render")
        self.assertEqual(
            [item["source_id"] for item in artifact["metadata"]["image_bindings"]],
            [red.id, blue.id],
        )
        self.assertEqual(artifact["metadata"]["audio_binding"]["source_id"], audio.id)
        self.assertLess(abs(result["output"]["duration_us"] - 4_000_000), 180_000)

        path = self.store.resolve_project_file(
            self.project_id,
            result["output"]["path"],
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        first = self._rgb_at(path, 0.75)
        second = self._rgb_at(path, 3.0)
        self.assertGreater(first[0], first[2] + 80)
        self.assertGreater(second[2], second[0] + 80)

        probe = self._probe(path)
        streams = probe["streams"]
        self.assertEqual(len([s for s in streams if s["codec_type"] == "video"]), 1)
        self.assertEqual(len([s for s in streams if s["codec_type"] == "audio"]), 1)

    def test_visualizer_keeps_master_audio_duration_and_optional_artwork(self) -> None:
        audio = self._audio("visualizer-master.wav", 880, 3)
        artwork = self._image("cover.png", "green")

        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/audio.visualize/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {
                    "audio_source_id": audio.id,
                    "artwork_source_id": artwork.id,
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["result"]
        artifact = result["artifact"]
        metadata = artifact["metadata"]
        self.assertEqual(metadata["lifecycle"], "audio_visualizer_render")
        self.assertEqual(metadata["audio_binding"]["source_id"], audio.id)
        self.assertEqual(metadata["artwork_binding"]["source_id"], artwork.id)
        self.assertLess(abs(result["output"]["duration_us"] - 3_000_000), 200_000)

        path = self.store.resolve_project_file(
            self.project_id,
            result["output"]["path"],
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        probe = self._probe(path)
        streams = probe["streams"]
        videos = [s for s in streams if s["codec_type"] == "video"]
        audios = [s for s in streams if s["codec_type"] == "audio"]
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["codec_name"], "h264")
        self.assertEqual(len(audios), 1)
        self.assertEqual(audios[0]["codec_name"], "aac")

    def test_local_media_capabilities_fail_closed_after_registered_source_substitution(self) -> None:
        image = self._image("trusted.png", "red")
        path = self.store.resolve_project_file(
            self.project_id,
            image.path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        path.write_bytes(path.read_bytes() + b"substituted")

        response = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/video.compose_photos/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {"image_source_ids": [image.id]},
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("no longer matches", str(response.json()).lower())
        self.assertFalse(self.store.load_project(self.project_id).artifacts)


if __name__ == "__main__":
    unittest.main()
