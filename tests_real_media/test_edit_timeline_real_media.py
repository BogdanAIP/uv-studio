from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.projects import EDIT_STATE_PATH, ProjectStore
from uv_studio.server import app

WIDTH = 160
HEIGHT = 90
FPS = 30


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


def _color(path: Path, *, color: str, duration_s: int) -> None:
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration_s}",
        "-map",
        "0:v:0",
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-pix_fmt",
        "yuv420p",
        str(path),
    )


def _sample_rgb(path: Path, timestamp_s: float) -> tuple[int, int, int]:
    completed = subprocess.run(
        [
            _tool("ffmpeg"),
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp_s:.6f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=1:1:flags=neighbor",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=90,
        shell=False,
    )
    if len(completed.stdout) < 3:
        raise AssertionError(f"could not sample {path.name} at {timestamp_s}")
    return completed.stdout[0], completed.stdout[1], completed.stdout[2]


def _assert_color(test: unittest.TestCase, rgb: tuple[int, int, int], channel: str) -> None:
    index = {"red": 0, "green": 1, "blue": 2}[channel]
    dominant = rgb[index]
    others = [value for offset, value in enumerate(rgb) if offset != index]
    test.assertGreater(dominant, 70, (channel, rgb))
    test.assertGreater(dominant - max(others), 45, (channel, rgb))


class NonDestructiveTimelineRealMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Two accepted edits")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.source = self.project_dir / "sources" / "blue-source.mkv"
        self.red = self.project_dir / "artifacts" / "red-replacement.mkv"
        self.green = self.project_dir / "artifacts" / "green-replacement.mkv"
        _color(self.source, color="blue", duration_s=6)
        _color(self.red, color="red", duration_s=1)
        _color(self.green, color="green", duration_s=1)
        app.dependency_overrides[get_project_store] = lambda: self.store
        # API tests run before explicit FFmpeg provisioning in the same CI job and may
        # have cached an unavailable local offer. Rebuild after provisioning here.
        get_capability_registry.cache_clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        get_capability_registry.cache_clear()
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_accept_two_edits_stays_lightweight_until_one_explicit_render(self) -> None:
        artifacts_before_accept = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        for payload in (
            {
                "edit_id": "edit_red",
                "source_path": "sources/blue-source.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "replacement_path": "artifacts/red-replacement.mkv",
            },
            {
                "edit_id": "edit_green",
                "source_path": "sources/blue-source.mkv",
                "start_us": 4_000_000,
                "end_us": 5_000_000,
                "replacement_path": "artifacts/green-replacement.mkv",
            },
        ):
            accepted = self.client.post(
                f"/api/uv/projects/{self.project.project_id}/edits",
                json=payload,
            )
            self.assertEqual(accepted.status_code, 201, accepted.text)

        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            artifacts_before_accept,
        )
        self.assertTrue((self.project_dir / EDIT_STATE_PATH).is_file())
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

        registry = get_capability_registry()
        offer = registry.get_offer("local_ffmpeg.video_render_edits")
        self.assertEqual(offer.capability_id, "video.render_edits")
        self.assertEqual(offer.availability.value, "available")

        rendered = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/video.render_edits/execute",
            json={"input": {"source_path": "sources/blue-source.mkv"}},
        )
        self.assertEqual(rendered.status_code, 200, rendered.text)
        envelope = rendered.json()
        self.assertEqual(envelope["selection"]["offer"]["offer_id"], "local_ffmpeg.video_render_edits")
        result = envelope["result"]
        self.assertEqual(result["output"]["edit_ids"], ["edit_red", "edit_green"])
        output = self.project_dir / result["output"]["path"]
        self.assertTrue(output.is_file())
        self.assertEqual(len(self.store.load_project(self.project.project_id).artifacts), 1)

        for timestamp, expected in (
            (0.5, "blue"),
            (1.5, "red"),
            (2.5, "blue"),
            (4.5, "green"),
            (5.5, "blue"),
        ):
            _assert_color(self, _sample_rgb(output, timestamp), expected)


if __name__ == "__main__":
    unittest.main()
