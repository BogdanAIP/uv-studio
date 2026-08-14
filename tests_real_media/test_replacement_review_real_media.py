from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.projects import get_project_store
from uv_studio.projects import (
    ContinuityEvidence,
    ProjectReference,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementPlanProposal,
    ReplacementPlanStore,
    ReviewTarget,
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
    index = {"red": 0, "blue": 2}[channel]
    dominant = rgb[index]
    others = [value for offset, value in enumerate(rgb) if offset != index]
    test.assertGreater(dominant, 70, (channel, rgb))
    test.assertGreater(dominant - max(others), 45, (channel, rgb))


class ReplacementReviewRealMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Replacement review real media")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.source = self.project_dir / "sources" / "source.mkv"
        self.prepared = self.project_dir / "assets" / "prepared-red.mkv"
        _color(self.source, color="blue", duration_s=3)
        _color(self.prepared, color="red", duration_s=1)
        source_bytes = self.source.read_bytes()
        self.store.update_project(
            self.project.project_id,
            sources=(
                ProjectReference(
                    id="src_review",
                    kind="video",
                    path="sources/source.mkv",
                    metadata={
                        "sha256": hashlib.sha256(source_bytes).hexdigest(),
                        "size_bytes": len(source_bytes),
                    },
                ),
            ),
        )
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
                review_targets=(
                    ReviewTarget(
                        target_id="review_visual",
                        criterion="The reviewed candidate must replace only the requested second and remain visually coherent.",
                        required=True,
                        evidence_ids=("requested",),
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
        get_capability_registry.cache_clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        get_capability_registry.cache_clear()
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_real_candidate_review_acceptance_and_render_preserve_exact_range(self) -> None:
        original_source = self.source.read_bytes()
        candidate_response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/replacement-candidates/prepared-asset",
            json={
                "edit_id": "edit_1",
                "source_path": "assets/prepared-red.mkv",
            },
        )
        self.assertEqual(candidate_response.status_code, 200, candidate_response.text)
        candidate = candidate_response.json()["candidate"]
        candidate_path = self.project_dir / candidate["artifact_path"]
        self.assertTrue(candidate_path.is_file())
        self.assertEqual(candidate_path.read_bytes(), self.prepared.read_bytes())
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

        review_response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/replacement-reviews",
            json={
                "candidate_id": candidate["candidate_id"],
                "verdict": "approved",
                "observations": [
                    {
                        "observation_id": "obs_visual",
                        "kind": "observation",
                        "statement": "The exact red candidate is suitable for the requested one-second replacement range.",
                        "confidence": "high",
                        "evidence": [
                            {"kind": "brief_evidence", "ref_id": "requested"},
                            {
                                "kind": "candidate_artifact",
                                "ref_id": candidate["artifact_id"],
                            },
                        ],
                    }
                ],
                "assessments": [
                    {
                        "target_id": "review_visual",
                        "outcome": "pass",
                        "observation_ids": ["obs_visual"],
                    }
                ],
            },
        )
        self.assertEqual(review_response.status_code, 201, review_response.text)
        review = review_response.json()
        self.assertEqual(review["candidate_id"], candidate["candidate_id"])
        self.assertEqual(review["plan_sha256"], candidate["plan_sha256"])
        self.assertEqual((review["start_us"], review["end_us"]), (1_000_000, 2_000_000))
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

        accepted_response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/replacement-reviews/{review['review_id']}/accept"
        )
        self.assertEqual(accepted_response.status_code, 201, accepted_response.text)
        accepted = accepted_response.json()["edits"]
        self.assertEqual(len(accepted), 1)
        edit = accepted[0]
        self.assertEqual(edit["edit_id"], "edit_1")
        self.assertEqual(edit["source_path"], "sources/source.mkv")
        self.assertEqual((edit["start_us"], edit["end_us"]), (1_000_000, 2_000_000))
        self.assertEqual(edit["replacement_path"], candidate["artifact_path"])
        self.assertEqual(self.source.read_bytes(), original_source)

        rendered_response = self.client.post(
            f"/api/uv/projects/{self.project.project_id}/capabilities/video.render_edits/execute",
            json={"input": {"source_path": "sources/source.mkv"}},
        )
        self.assertEqual(rendered_response.status_code, 200, rendered_response.text)
        envelope = rendered_response.json()
        self.assertEqual(
            envelope["selection"]["offer"]["offer_id"],
            "local_ffmpeg.video_render_edits",
        )
        output = self.project_dir / envelope["result"]["output"]["path"]
        self.assertTrue(output.is_file())
        self.assertEqual(envelope["result"]["output"]["edit_ids"], ["edit_1"])
        _assert_color(self, _sample_rgb(output, 0.5), "blue")
        _assert_color(self, _sample_rgb(output, 1.5), "red")
        _assert_color(self, _sample_rgb(output, 2.5), "blue")
        self.assertEqual(self.source.read_bytes(), original_source)


if __name__ == "__main__":
    unittest.main()
