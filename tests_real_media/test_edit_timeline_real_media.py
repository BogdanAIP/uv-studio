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
from uv_studio.projects import (
    AcceptedRangeEdit,
    EDIT_STATE_PATH,
    ProjectStore,
    RangeEditStateStore,
)
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


def _color(
    path: Path,
    *,
    color: str,
    duration_s: int,
    width: int = WIDTH,
    height: int = HEIGHT,
    audio: bool = False,
    tone_hz: int = 440,
) -> None:
    args = [
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={width}x{height}:r={FPS}:d={duration_s}",
    ]
    if audio:
        args += [
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={tone_hz}:sample_rate=48000:duration={duration_s}",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
        ]
    else:
        args += ["-map", "0:v:0"]
    args += ["-c:v", "ffv1", "-level", "3", "-pix_fmt", "yuv420p"]
    if audio:
        args += ["-c:a", "flac", "-sample_fmt", "s16", "-shortest"]
    args.append(str(path))
    _ffmpeg(*args)


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


def _stream_types(path: Path) -> list[str]:
    completed = subprocess.run(
        [
            _tool("ffprobe"),
            "-v",
            "error",
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
    probe = json.loads(completed.stdout)
    return [str(stream.get("codec_type")) for stream in probe.get("streams", [])]


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
        self.wrong_size = self.project_dir / "artifacts" / "wrong-size-replacement.mkv"
        _color(self.source, color="blue", duration_s=6)
        _color(self.red, color="red", duration_s=1)
        _color(self.green, color="green", duration_s=1)
        _color(
            self.wrong_size,
            color="yellow",
            duration_s=1,
            width=128,
            height=72,
        )
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

    def _render_url(self) -> str:
        return (
            f"/api/uv/projects/{self.project.project_id}"
            "/capabilities/video.render_edits/execute"
        )

    def _accept(self, payload: dict[str, object]) -> None:
        RangeEditStateStore(self.store).accept(
            self.project.project_id,
            AcceptedRangeEdit(
                edit_id=str(payload["edit_id"]),
                source_path=str(payload["source_path"]),
                start_us=int(payload["start_us"]),
                end_us=int(payload["end_us"]),
                replacement_path=str(payload["replacement_path"]),
            ),
        )

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
            self._accept(payload)

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
            self._render_url(),
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

    def test_multi_edit_audio_branch_renders_one_video_and_one_audio_stream(self) -> None:
        source = self.project_dir / "sources" / "audio-blue-source.mkv"
        red = self.project_dir / "artifacts" / "audio-red-replacement.mkv"
        green = self.project_dir / "artifacts" / "audio-green-replacement.mkv"
        _color(source, color="blue", duration_s=6, audio=True, tone_hz=440)
        _color(red, color="red", duration_s=1, audio=True, tone_hz=660)
        _color(green, color="green", duration_s=1, audio=True, tone_hz=880)
        artifacts_before_accept = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())

        self._accept(
            {
                "edit_id": "audio_red",
                "source_path": "sources/audio-blue-source.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "replacement_path": "artifacts/audio-red-replacement.mkv",
            }
        )
        self._accept(
            {
                "edit_id": "audio_green",
                "source_path": "sources/audio-blue-source.mkv",
                "start_us": 4_000_000,
                "end_us": 5_000_000,
                "replacement_path": "artifacts/audio-green-replacement.mkv",
            }
        )
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            artifacts_before_accept,
        )
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

        rendered = self.client.post(
            self._render_url(),
            json={"input": {"source_path": "sources/audio-blue-source.mkv"}},
        )
        self.assertEqual(rendered.status_code, 200, rendered.text)
        result = rendered.json()["result"]
        self.assertEqual(result["output"]["edit_ids"], ["audio_red", "audio_green"])
        output = self.project_dir / result["output"]["path"]
        self.assertEqual(sorted(_stream_types(output)), ["audio", "video"])
        for timestamp, expected in (
            (0.5, "blue"),
            (1.5, "red"),
            (2.5, "blue"),
            (4.5, "green"),
            (5.5, "blue"),
        ):
            _assert_color(self, _sample_rgb(output, timestamp), expected)

    def test_acceptance_is_storage_only_and_incompatible_media_fails_at_render(self) -> None:
        artifacts_before_accept = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        self._accept(
            {
                "edit_id": "edit_wrong_size",
                "source_path": "sources/blue-source.mkv",
                "start_us": 2_000_000,
                "end_us": 3_000_000,
                "replacement_path": "artifacts/wrong-size-replacement.mkv",
            }
        )
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            artifacts_before_accept,
        )
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

        rendered = self.client.post(
            self._render_url(),
            json={"input": {"source_path": "sources/blue-source.mkv"}},
        )
        self.assertEqual(rendered.status_code, 422, rendered.text)
        self.assertIn("resolution must match", rendered.text)
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())
        self.assertEqual(
            sorted(path.name for path in (self.project_dir / "artifacts").iterdir()),
            artifacts_before_accept,
        )


if __name__ == "__main__":
    unittest.main()
