from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    ContinuityEvidence,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementPlanProposal,
    ReplacementPlanStore,
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


def _probe(path: Path) -> dict:
    completed = subprocess.run(
        [
            _tool("ffprobe"),
            "-v",
            "error",
            "-show_streams",
            "-show_format",
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
    return completed.stdout[0], completed.stdout[1], completed.stdout[2]


class ReplacementPreparationRealMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Prepared candidate real media")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.source = self.project_dir / "sources" / "source.mkv"
        self.prepared = self.project_dir / "assets" / "prepared-red.mkv"
        _color(self.source, color="blue", duration_s=3)
        _color(self.prepared, color="red", duration_s=1)
        RangeContinuityBriefStore(self.store).upsert(
            self.project.project_id,
            RangeContinuityBrief(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                evidence=(
                    ContinuityEvidence(
                        evidence_id="requested",
                        role="requested",
                        path="sources/source.mkv",
                        source_start_us=1_000_000,
                        source_end_us=2_000_000,
                    ),
                ),
            ),
        )
        ReplacementPlanStore(self.store).approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class="prepared_asset",
                goal="Use the prepared one-second red replacement.",
                required_changes=("Use the prepared red clip.",),
            ),
        )
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_real_prepared_video_becomes_candidate_but_not_accepted_edit(self) -> None:
        original_bytes = self.prepared.read_bytes()
        response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/replacement-candidates/prepared-asset",
            json={
                "edit_id": "edit_1",
                "source_path": "assets/prepared-red.mkv",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        candidate = response.json()["candidate"]
        artifact_path = self.project_dir / candidate["artifact_path"]

        self.assertTrue(artifact_path.is_file())
        self.assertEqual(artifact_path.read_bytes(), original_bytes)
        self.assertEqual(candidate["stage"], "full")
        self.assertEqual(candidate["method_class"], "prepared_asset")
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

        probe = _probe(artifact_path)
        stream_types = [str(item.get("codec_type")) for item in probe.get("streams", [])]
        self.assertEqual(stream_types, ["video"])
        duration = float(probe["format"]["duration"])
        self.assertAlmostEqual(duration, 1.0, delta=0.05)
        rgb = _sample_rgb(artifact_path, 0.5)
        self.assertGreater(rgb[0], 70, rgb)
        self.assertGreater(rgb[0] - max(rgb[1], rgb[2]), 45, rgb)

        project = self.store.load_project(self.project.project_id)
        self.assertEqual(len(project.artifacts), 1)
        self.assertEqual(project.artifacts[0].id, candidate["artifact_id"])
        self.assertEqual(project.artifacts[0].path, candidate["artifact_path"])


if __name__ == "__main__":
    unittest.main()
