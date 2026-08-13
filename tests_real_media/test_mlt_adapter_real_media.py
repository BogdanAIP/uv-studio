from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities import build_builtin_capability_registry
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.editor import MLTTimelineAdapter
from uv_studio.projects import AcceptedRangeEdit, RangeEditStateStore
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore

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


def _color(path: Path, color: str, duration_s: int) -> None:
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


def _sample_rgb(path: Path, timestamp_s: float) -> tuple[int, int, int]:
    completed = subprocess.run(
        [
            _tool("ffmpeg"),
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp_s:.3f}",
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
        raise AssertionError(
            f"could not sample {path.name} at {timestamp_s}s; probe={_probe(path)!r}"
        )
    return completed.stdout[0], completed.stdout[1], completed.stdout[2]


def _assert_color(test: unittest.TestCase, rgb: tuple[int, int, int], channel: str) -> None:
    index = {"red": 0, "green": 1, "blue": 2}[channel]
    dominant = rgb[index]
    others = [value for offset, value in enumerate(rgb) if offset != index]
    test.assertGreater(dominant, 70, (channel, rgb))
    test.assertGreater(dominant - max(others), 45, (channel, rgb))


class MLTAdapterParityRealMediaTests(unittest.TestCase):
    def test_mlt_derived_projection_matches_authoritative_render_on_exact_cfr_boundaries(self) -> None:
        _tool("melt")
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="MLT adapter parity")
            project_dir = store.project_directory(project.project_id)
            source = project_dir / "sources" / "blue.mkv"
            red = project_dir / "artifacts" / "red.mkv"
            green = project_dir / "artifacts" / "green.mkv"
            _color(source, "blue", 6)
            _color(red, "red", 1)
            _color(green, "green", 1)

            source_ref = ProjectReference(
                id="src_blue",
                kind="video",
                path="sources/blue.mkv",
                metadata={
                    "duration_us": 6_000_000,
                    "width": WIDTH,
                    "height": HEIGHT,
                    "avg_frame_rate": "30/1",
                    "has_audio": False,
                },
            )
            red_ref = ProjectReference(id="art_red", kind="video", path="artifacts/red.mkv")
            green_ref = ProjectReference(id="art_green", kind="video", path="artifacts/green.mkv")
            store.update_project(
                project.project_id,
                sources=(source_ref,),
                artifacts=(red_ref, green_ref),
            )
            edits = RangeEditStateStore(store)
            edits.accept(
                project.project_id,
                AcceptedRangeEdit(
                    edit_id="edit_red",
                    source_path=source_ref.path,
                    start_us=1_000_000,
                    end_us=2_000_000,
                    replacement_path=red_ref.path,
                ),
            )
            edits.accept(
                project.project_id,
                AcceptedRangeEdit(
                    edit_id="edit_green",
                    source_path=source_ref.path,
                    start_us=4_000_000,
                    end_us=5_000_000,
                    replacement_path=green_ref.path,
                ),
            )

            mlt = MLTTimelineAdapter(store)
            projection = mlt.project_timeline(project.project_id, source_ref.path)
            self.assertTrue(projection.exact_boundaries)
            self.assertEqual(projection.accepted_edit_ids, ("edit_red", "edit_green"))
            self.assertEqual(
                [segment.role for segment in projection.segments],
                ["source", "replacement", "source", "replacement", "source"],
            )
            mlt_output = Path(tmp) / "mlt-derived.mp4"
            mlt.render_projection(projection, mlt_output)
            mlt_probe = _probe(mlt_output)
            self.assertEqual(
                next(
                    stream.get("codec_name")
                    for stream in mlt_probe.get("streams", [])
                    if stream.get("codec_type") == "video"
                ),
                "mpeg4",
            )
            self.assertAlmostEqual(float(mlt_probe["format"]["duration"]), 6.0, delta=0.15)

            registry = build_builtin_capability_registry()
            authoritative = LocalFFmpegAdapter(store).execute(
                project_id=project.project_id,
                offer=registry.get_offer("local_ffmpeg.video_render_edits"),
                payload={"source_path": source_ref.path},
            )
            ffmpeg_output = project_dir / authoritative.output["path"]

            expected = (
                (0.5, "blue"),
                (1.5, "red"),
                (2.5, "blue"),
                (4.5, "green"),
                (5.5, "blue"),
            )
            evidence = []
            for timestamp, color in expected:
                mlt_rgb = _sample_rgb(mlt_output, timestamp)
                ffmpeg_rgb = _sample_rgb(ffmpeg_output, timestamp)
                _assert_color(self, mlt_rgb, color)
                _assert_color(self, ffmpeg_rgb, color)
                evidence.append(
                    {
                        "timestamp_s": timestamp,
                        "expected": color,
                        "mlt_rgb": mlt_rgb,
                        "authoritative_rgb": ffmpeg_rgb,
                    }
                )

            report_path = Path(tmp) / "mlt-parity.json"
            report_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            self.assertTrue(report_path.is_file())


if __name__ == "__main__":
    unittest.main()
