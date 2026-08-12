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
from uv_studio.capabilities.execution import CapabilityToolFailed
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.store import ProjectStore


WIDTH = 160
HEIGHT = 90
FPS = 30
DURATION_TOLERANCE_US = 120_000
_EVIDENCE: dict[str, object] = {"cases": {}}


def _required_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise AssertionError(f"required real-media tool is missing: {name}")
    return path


def _run_text(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
        timeout=90,
        shell=False,
    )


def _run_bytes(command: list[str]) -> bytes:
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        timeout=90,
        shell=False,
    )
    return completed.stdout


def _ffmpeg(*args: str) -> None:
    completed = _run_text([_required_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *args])
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)


def _probe(path: Path) -> dict:
    completed = _run_text(
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
    )
    return json.loads(completed.stdout)


def _duration_us(path: Path) -> int:
    probe = _probe(path)
    raw = probe.get("format", {}).get("duration")
    if raw not in (None, "N/A"):
        return round(float(raw) * 1_000_000)
    durations = [
        round(float(stream["duration"]) * 1_000_000)
        for stream in probe.get("streams", [])
        if stream.get("duration") not in (None, "N/A")
    ]
    if not durations:
        raise AssertionError(f"no measurable duration for {path.name}")
    return max(durations)


def _stream_types(path: Path) -> list[str]:
    return [str(stream.get("codec_type")) for stream in _probe(path).get("streams", [])]


def _video_frame_timestamps_us(path: Path) -> list[int]:
    completed = _run_text(
        [
            _required_tool("ffprobe"),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    result: list[int] = []
    for line in completed.stdout.splitlines():
        value = line.strip().split(",", 1)[0]
        if not value or value == "N/A":
            continue
        result.append(round(float(value) * 1_000_000))
    return result


def _frame_deltas_us(path: Path) -> list[int]:
    timestamps = _video_frame_timestamps_us(path)
    return [later - earlier for earlier, later in zip(timestamps, timestamps[1:]) if later > earlier]


def _sample_rgb(path: Path, timestamp_s: float) -> tuple[int, int, int]:
    raw = _run_bytes(
        [
            _required_tool("ffmpeg"),
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
        ]
    )
    if len(raw) < 3:
        raise AssertionError(f"could not sample a frame from {path.name} at {timestamp_s}")
    return raw[0], raw[1], raw[2]


def _assert_dominant(test: unittest.TestCase, rgb: tuple[int, int, int], channel: str) -> None:
    index = {"red": 0, "green": 1, "blue": 2}[channel]
    dominant = rgb[index]
    others = [value for offset, value in enumerate(rgb) if offset != index]
    test.assertGreater(dominant, 70, (channel, rgb))
    test.assertGreater(dominant - max(others), 45, (channel, rgb))


def _generate_color_media(
    path: Path,
    *,
    color: str,
    duration_s: float,
    audio: bool,
    tone_hz: int = 440,
    output_ts_offset_s: float | None = None,
) -> None:
    args = [
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration_s}",
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
    if output_ts_offset_s is not None:
        args += ["-output_ts_offset", f"{output_ts_offset_s:.6f}"]
    args.append(str(path))
    _ffmpeg(*args)


def _generate_vfr_media(path: Path) -> None:
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=s={WIDTH}x{HEIGHT}:r={FPS}:d=3",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=523:sample_rate=48000:duration=3",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        r"select=if(lt(t\,1.5)\,not(mod(n\,2))\,1)",
        "-fps_mode",
        "vfr",
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "flac",
        "-sample_fmt",
        "s16",
        "-shortest",
        str(path),
    )


def _generate_offset_marker_media(path: Path) -> None:
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        f"color=c=blue:s={WIDTH}x{HEIGHT}:r={FPS}:d=1",
        "-f",
        "lavfi",
        "-i",
        f"color=c=green:s={WIDTH}x{HEIGHT}:r={FPS}:d=1",
        "-f",
        "lavfi",
        "-i",
        f"color=c=red:s={WIDTH}x{HEIGHT}:r={FPS}:d=1",
        "-filter_complex",
        "[0:v:0][1:v:0][2:v:0]concat=n=3:v=1:a=0[v]",
        "-map",
        "[v]",
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-pix_fmt",
        "yuv420p",
        "-output_ts_offset",
        "1.250000",
        str(path),
    )


def _offer(offer_id: str, capability_id: str) -> CapabilityOffer:
    return CapabilityOffer(
        offer_id,
        capability_id,
        "local_ffmpeg",
        f"Real media {capability_id}",
        OfferAvailability.AVAILABLE,
        "real-media-golden",
        LocalityClass.LOCAL,
        CostClass.FREE,
        False,
    )


def _record_case(name: str, **facts: object) -> None:
    cases = _EVIDENCE.setdefault("cases", {})
    assert isinstance(cases, dict)
    cases[name] = facts


def tearDownModule() -> None:
    destination = os.environ.get("UV_REAL_MEDIA_REPORT")
    if not destination:
        return
    report_path = Path(destination)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(_EVIDENCE, indent=2, sort_keys=True), encoding="utf-8")


class RealMediaRangeGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ffmpeg = _required_tool("ffmpeg")
        ffprobe = _required_tool("ffprobe")
        ffmpeg_version = _run_text([ffmpeg, "-version"]).stdout.splitlines()[0]
        ffprobe_version = _run_text([ffprobe, "-version"]).stdout.splitlines()[0]
        _EVIDENCE.update(
            {
                "platform": platform.system(),
                "ffmpeg": ffmpeg_version,
                "ffprobe": ffprobe_version,
            }
        )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Stage 4A real media")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.adapter = LocalFFmpegAdapter(self.store)
        self.extract_offer = _offer(
            "local_ffmpeg.video_extract_range", "video.extract_range"
        )
        self.replace_offer = _offer(
            "local_ffmpeg.video_replace_range", "video.replace_range"
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _project_path(self, relative: str) -> Path:
        return self.project_dir / relative

    def _assert_duration(self, path: Path, expected_us: int) -> int:
        actual = _duration_us(path)
        self.assertLessEqual(abs(actual - expected_us), DURATION_TOLERANCE_US, (path.name, actual))
        return actual

    def test_cfr_audio_extract_and_reinsert_are_real_and_observable(self) -> None:
        source = self._project_path("sources/cfr-audio.mkv")
        replacement = self._project_path("artifacts/replacement-red-audio.mkv")
        _generate_color_media(source, color="blue", duration_s=4, audio=True, tone_hz=440)
        _generate_color_media(
            replacement, color="red", duration_s=1, audio=True, tone_hz=880
        )

        extraction = self.adapter.execute(
            project_id=self.project.project_id,
            offer=self.extract_offer,
            payload={
                "source_path": "sources/cfr-audio.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
                "context_before_us": 500_000,
                "context_after_us": 500_000,
            },
        )
        self.assertEqual(extraction.output["range"]["requested"]["start_us"], 1_000_000)
        self.assertEqual(extraction.output["range"]["requested"]["end_us"], 2_000_000)
        requested = self._project_path(extraction.output["requested_path"])
        before = self._project_path(extraction.output["context_before_path"])
        after = self._project_path(extraction.output["context_after_path"])
        self.assertTrue(requested.is_file())
        self.assertEqual(sorted(_stream_types(requested)), ["audio", "video"])
        requested_duration_us = self._assert_duration(requested, 1_000_000)
        self._assert_duration(before, 500_000)
        self._assert_duration(after, 500_000)

        started = time.perf_counter()
        composed = self.adapter.execute(
            project_id=self.project.project_id,
            offer=self.replace_offer,
            payload={
                "source_path": "sources/cfr-audio.mkv",
                "replacement_path": "artifacts/replacement-red-audio.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
            },
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        output = self._project_path(composed.output["path"])
        self.assertTrue(output.is_file())
        self.assertEqual(sorted(_stream_types(output)), ["audio", "video"])
        output_duration_us = self._assert_duration(output, 4_000_000)

        _assert_dominant(self, _sample_rgb(output, 0.5), "blue")
        _assert_dominant(self, _sample_rgb(output, 1.5), "red")
        _assert_dominant(self, _sample_rgb(output, 2.5), "blue")

        _record_case(
            "cfr_audio_reinsertion",
            requested_duration_us=requested_duration_us,
            output_duration_us=output_duration_us,
            source_bytes=source.stat().st_size,
            replacement_bytes=replacement.stat().st_size,
            output_bytes=output.stat().st_size,
            output_to_source_size_ratio=round(output.stat().st_size / source.stat().st_size, 3),
            reinsertion_elapsed_ms=elapsed_ms,
        )

    def test_vfr_audio_extraction_preserves_observable_variable_intervals(self) -> None:
        source = self._project_path("sources/vfr-audio.mkv")
        _generate_vfr_media(source)
        source_deltas = _frame_deltas_us(source)
        self.assertTrue(any(delta >= 55_000 for delta in source_deltas), source_deltas[:20])
        self.assertTrue(any(delta <= 45_000 for delta in source_deltas), source_deltas[:20])

        extraction = self.adapter.execute(
            project_id=self.project.project_id,
            offer=self.extract_offer,
            payload={
                "source_path": "sources/vfr-audio.mkv",
                "start_us": 500_000,
                "end_us": 2_500_000,
            },
        )
        requested = self._project_path(extraction.output["requested_path"])
        requested_deltas = _frame_deltas_us(requested)
        self.assertTrue(any(delta >= 55_000 for delta in requested_deltas), requested_deltas[:20])
        self.assertTrue(any(delta <= 45_000 for delta in requested_deltas), requested_deltas[:20])
        self.assertEqual(sorted(_stream_types(requested)), ["audio", "video"])
        requested_duration_us = self._assert_duration(requested, 2_000_000)

        _record_case(
            "vfr_audio_extraction",
            requested_duration_us=requested_duration_us,
            source_distinct_frame_deltas_us=sorted(set(source_deltas)),
            extracted_distinct_frame_deltas_us=sorted(set(requested_deltas)),
        )

    def test_no_audio_extract_and_reinsert_keep_audio_absent(self) -> None:
        source = self._project_path("sources/no-audio.mkv")
        replacement = self._project_path("artifacts/replacement-red-no-audio.mkv")
        _generate_color_media(source, color="blue", duration_s=3, audio=False)
        _generate_color_media(replacement, color="red", duration_s=1, audio=False)

        extraction = self.adapter.execute(
            project_id=self.project.project_id,
            offer=self.extract_offer,
            payload={
                "source_path": "sources/no-audio.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
            },
        )
        requested = self._project_path(extraction.output["requested_path"])
        self.assertEqual(_stream_types(requested), ["video"])

        composed = self.adapter.execute(
            project_id=self.project.project_id,
            offer=self.replace_offer,
            payload={
                "source_path": "sources/no-audio.mkv",
                "replacement_path": "artifacts/replacement-red-no-audio.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
            },
        )
        output = self._project_path(composed.output["path"])
        self.assertEqual(_stream_types(output), ["video"])
        self._assert_duration(output, 3_000_000)
        _assert_dominant(self, _sample_rgb(output, 0.5), "blue")
        _assert_dominant(self, _sample_rgb(output, 1.5), "red")
        _assert_dominant(self, _sample_rgb(output, 2.5), "blue")

        _record_case(
            "no_audio_reinsertion",
            output_bytes=output.stat().st_size,
            audio_streams=0,
        )

    def test_offset_timestamp_source_uses_zero_based_project_range(self) -> None:
        source = self._project_path("sources/offset-markers.mkv")
        _generate_offset_marker_media(source)
        source_probe = _probe(source)
        video = next(stream for stream in source_probe["streams"] if stream["codec_type"] == "video")
        source_start_us = round(float(video["start_time"]) * 1_000_000)
        self.assertGreaterEqual(source_start_us, 1_000_000)

        extraction = self.adapter.execute(
            project_id=self.project.project_id,
            offer=self.extract_offer,
            payload={
                "source_path": "sources/offset-markers.mkv",
                "start_us": 750_000,
                "end_us": 1_750_000,
            },
        )
        requested = self._project_path(extraction.output["requested_path"])
        self._assert_duration(requested, 1_000_000)
        _assert_dominant(self, _sample_rgb(requested, 0.10), "blue")
        _assert_dominant(self, _sample_rgb(requested, 0.80), "green")
        self.assertEqual(extraction.output["range"]["requested"]["start_us"], 750_000)
        self.assertEqual(extraction.output["range"]["requested"]["end_us"], 1_750_000)

        _record_case(
            "offset_timestamp_extraction",
            source_start_us=source_start_us,
            requested_start_us=750_000,
            requested_end_us=1_750_000,
        )

    def test_real_first_output_is_removed_when_later_extraction_step_fails(self) -> None:
        source = self._project_path("sources/rollback.mkv")
        _generate_color_media(source, color="blue", duration_s=3, audio=False)
        ffmpeg_calls = 0

        def fault_injecting_real_runner(command, **kwargs):
            nonlocal ffmpeg_calls
            executable = Path(str(command[0])).name.lower()
            if executable.startswith("ffmpeg") and not executable.startswith("ffprobe"):
                ffmpeg_calls += 1
                if ffmpeg_calls == 2:
                    return subprocess.CompletedProcess(
                        command,
                        1,
                        stdout="",
                        stderr="injected second real-media extraction failure",
                    )
            return subprocess.run(command, **kwargs)

        adapter = LocalFFmpegAdapter(self.store, runner=fault_injecting_real_runner)
        with self.assertRaises(CapabilityToolFailed):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self.extract_offer,
                payload={
                    "source_path": "sources/rollback.mkv",
                    "start_us": 1_000_000,
                    "end_us": 2_000_000,
                    "context_before_us": 500_000,
                    "context_after_us": 500_000,
                },
            )

        self.assertGreaterEqual(ffmpeg_calls, 2)
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())
        self.assertEqual(list((self.project_dir / "artifacts").iterdir()), [])
        _record_case("rollback_after_real_output", ffmpeg_calls=ffmpeg_calls, artifacts_after_failure=0)


if __name__ == "__main__":
    unittest.main()
