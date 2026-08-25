from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.store import ProjectStore


WIDTH = 320
HEIGHT = 180
FPS = 30
SOURCE_DURATION_S = 8
REPLACEMENT_DURATION_S = 1
DURATION_TOLERANCE_US = 120_000


def _required_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise AssertionError(f"required real-media tool is missing: {name}")
    return path


def _run_text(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
        shell=False,
    )


def _ffmpeg(*args: str) -> None:
    completed = subprocess.run(
        [
            _required_tool("ffmpeg"),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            *args,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
        shell=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)


def _probe(path: Path) -> dict:
    return json.loads(
        _run_text(
            [
                _required_tool("ffprobe"),
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ]
        ).stdout
    )


def _video_codec(path: Path) -> str:
    video = next(
        stream for stream in _probe(path).get("streams", []) if stream.get("codec_type") == "video"
    )
    return str(video.get("codec_name"))


def _duration_us(path: Path) -> int:
    probe = _probe(path)
    raw = probe.get("format", {}).get("duration")
    if raw in (None, "N/A"):
        raise AssertionError(f"format duration is unavailable for {path.name}")
    return round(float(raw) * 1_000_000)


def _generate_mpeg4_testsrc(path: Path, *, duration_s: int, pattern: str) -> None:
    if pattern == "testsrc2":
        source = f"testsrc2=s={WIDTH}x{HEIGHT}:r={FPS}:d={duration_s}"
    elif pattern == "smptebars":
        source = f"smptebars=s={WIDTH}x{HEIGHT}:r={FPS}:d={duration_s}"
    else:
        raise ValueError(pattern)
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        source,
        "-map",
        "0:v:0",
        "-c:v",
        "mpeg4",
        "-q:v",
        "7",
        "-pix_fmt",
        "yuv420p",
        str(path),
    )


def _offer() -> CapabilityOffer:
    return CapabilityOffer(
        "local_ffmpeg.video_replace_range",
        "video.replace_range",
        "local_ffmpeg",
        "Real compressed-source reinsertion evidence",
        OfferAvailability.AVAILABLE,
        "real-media-golden",
        LocalityClass.LOCAL,
        CostClass.FREE,
        False,
    )


def _report_path() -> Path | None:
    destination = os.environ.get("UV_REAL_MEDIA_REPORT")
    if not destination:
        return None
    path = Path(destination)
    return path.with_name(f"{path.stem}-compressed{path.suffix}")


class CompressedSourceReinsertionEvidenceTests(unittest.TestCase):
    def test_mpeg4_source_exposes_whole_output_ffv1_size_and_time_cost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(recipe_id="general_video", title="Compressed reinsertion evidence")
            project_dir = store.project_directory(project.project_id)
            source = project_dir / "sources" / "compressed-source.mkv"
            replacement = project_dir / "artifacts" / "compressed-replacement.mkv"

            _generate_mpeg4_testsrc(
                source,
                duration_s=SOURCE_DURATION_S,
                pattern="testsrc2",
            )
            _generate_mpeg4_testsrc(
                replacement,
                duration_s=REPLACEMENT_DURATION_S,
                pattern="smptebars",
            )
            self.assertEqual(_video_codec(source), "mpeg4")
            self.assertEqual(_video_codec(replacement), "mpeg4")

            started = time.perf_counter()
            result = LocalFFmpegAdapter(store).execute(
                project_id=project.project_id,
                offer=_offer(),
                payload={
                    "source_path": "sources/compressed-source.mkv",
                    "replacement_path": "artifacts/compressed-replacement.mkv",
                    "start_us": 3_000_000,
                    "end_us": 4_000_000,
                },
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            output = project_dir / result.output["path"]

            self.assertTrue(output.is_file())
            self.assertEqual(_video_codec(output), "ffv1")
            actual_duration_us = _duration_us(output)
            self.assertLessEqual(
                abs(actual_duration_us - SOURCE_DURATION_S * 1_000_000),
                DURATION_TOLERANCE_US,
            )

            source_bytes = source.stat().st_size
            output_bytes = output.stat().st_size
            ratio = output_bytes / source_bytes
            self.assertGreater(source_bytes, 0)
            self.assertGreater(output_bytes, 0)
            self.assertGreater(ratio, 0)

            report = {
                "platform": platform.system(),
                "ffmpeg": _run_text([_required_tool("ffmpeg"), "-version"]).stdout.splitlines()[0],
                "case": "mpeg4_to_whole_output_ffv1",
                "source_codec": "mpeg4",
                "output_codec": "ffv1",
                "width": WIDTH,
                "height": HEIGHT,
                "fps": FPS,
                "source_duration_us": SOURCE_DURATION_S * 1_000_000,
                "actual_output_duration_us": actual_duration_us,
                "source_bytes": source_bytes,
                "replacement_bytes": replacement.stat().st_size,
                "output_bytes": output_bytes,
                "output_to_source_size_ratio": round(ratio, 3),
                "reinsertion_elapsed_ms": elapsed_ms,
            }
            destination = _report_path()
            if destination is not None:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(
                    json.dumps(report, indent=2, sort_keys=True),
                    encoding="utf-8",
                )


if __name__ == "__main__":
    unittest.main()
