from __future__ import annotations

import json
import subprocess
import tempfile
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


class RangeExtractionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Range contract")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "clip.mkv").write_bytes(b"source")
        self.offer = CapabilityOffer(
            "local_ffmpeg.video_extract_range",
            "video.extract_range",
            "local_ffmpeg",
            "Range",
            OfferAvailability.AVAILABLE,
            "test",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _stream_duration_probe() -> dict:
        return {
            "format": {
                "duration": "N/A",
                "format_name": "matroska,webm",
                "size": "100",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "vp9",
                    "duration": "5.250001",
                    "avg_frame_rate": "0/0",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "opus",
                    "duration": "5.200000",
                },
            ],
        }

    def test_stream_duration_fallback_and_vfr_passthrough_are_explicit(self) -> None:
        calls: list[list[str]] = []

        def runner(command, **kwargs):
            calls.append(list(command))
            if command[0] == "fake-ffprobe":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(self._stream_duration_probe()),
                    stderr="",
                )
            Path(command[-1]).write_bytes(b"lossless-intermediate")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        result = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        ).execute(
            project_id=self.project.project_id,
            offer=self.offer,
            payload={
                "source_path": "sources/clip.mkv",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
            },
        )

        self.assertEqual(result.output["range"]["source_duration_us"], 5_250_001)
        self.assertEqual(len(calls), 2)
        ffmpeg = calls[1]
        self.assertEqual(ffmpeg[ffmpeg.index("-fps_mode") + 1], "passthrough")
        self.assertEqual(ffmpeg[ffmpeg.index("-c:v") + 1], "ffv1")
        self.assertEqual(ffmpeg[ffmpeg.index("-c:a") + 1], "flac")

        artifacts = self.store.load_project(self.project.project_id).artifacts
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0].metadata["lifecycle"], "intermediate")
        self.assertEqual(artifacts[0].metadata["range_role"], "requested")

    def test_zero_byte_success_is_rejected_and_removed(self) -> None:
        def runner(command, **kwargs):
            if command[0] == "fake-ffprobe":
                payload = self._stream_duration_probe()
                payload["format"]["duration"] = "5.0"
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(payload),
                    stderr="",
                )
            Path(command[-1]).write_bytes(b"")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with self.assertRaises(CapabilityToolFailed):
            LocalFFmpegAdapter(
                self.store,
                runner=runner,
                tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
            ).execute(
                project_id=self.project.project_id,
                offer=self.offer,
                payload={
                    "source_path": "sources/clip.mkv",
                    "start_us": 1_000_000,
                    "end_us": 2_000_000,
                },
            )

        self.assertEqual(list((self.project_dir / "artifacts").iterdir()), [])
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())


if __name__ == "__main__":
    unittest.main()
