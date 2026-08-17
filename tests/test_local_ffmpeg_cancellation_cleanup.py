from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import CapabilityExecutionCancelled
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.store import ProjectStore


class LocalFFmpegCancellationCleanupTests(unittest.TestCase):
    @staticmethod
    def _offer(capability_id: str, offer_id: str) -> CapabilityOffer:
        return CapabilityOffer(
            offer_id,
            capability_id,
            "local_ffmpeg",
            offer_id,
            OfferAvailability.AVAILABLE,
            "test",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    @staticmethod
    def _probe_payload() -> dict:
        return {
            "format": {"duration": "10.0", "format_name": "mov,mp4", "size": "1234"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                    "duration": "10.0",
                    "avg_frame_rate": "30/1",
                },
                {"codec_type": "audio", "codec_name": "aac", "duration": "10.0"},
            ],
        }

    def test_cancelled_range_extract_removes_partial_output_and_registers_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="cancel cleanup")
            project_dir = store.project_directory(project.project_id)
            source = project_dir / "sources" / "clip.mp4"
            source.write_bytes(b"source")

            def runner(command, **kwargs):
                if command[0] == "fake-ffprobe":
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout=json.dumps(self._probe_payload()),
                        stderr="",
                    )
                output = Path(command[-1])
                output.write_bytes(b"partial-ffmpeg-output")
                raise CapabilityExecutionCancelled("test cancellation after output opened")

            adapter = LocalFFmpegAdapter(
                store,
                runner=runner,
                tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
            )
            with self.assertRaises(CapabilityExecutionCancelled):
                adapter.execute(
                    project_id=project.project_id,
                    offer=self._offer(
                        "video.extract_range",
                        "local_ffmpeg.video_extract_range",
                    ),
                    payload={
                        "source_path": "sources/clip.mp4",
                        "start_us": 1_000_000,
                        "end_us": 2_000_000,
                    },
                )

            self.assertEqual(list((project_dir / "artifacts").iterdir()), [])
            self.assertEqual(store.load_project(project.project_id).artifacts, ())

    def test_allowlist_excludes_operations_without_transactional_cancel_rollback(self) -> None:
        self.assertTrue(LocalFFmpegAdapter.supports_cancellation("video.render_edits"))
        self.assertTrue(LocalFFmpegAdapter.supports_cancellation("video.render_music_video"))
        self.assertFalse(LocalFFmpegAdapter.supports_cancellation("timeline.assemble"))
        self.assertFalse(LocalFFmpegAdapter.supports_cancellation("video.render_dubbing"))


if __name__ == "__main__":
    unittest.main()
