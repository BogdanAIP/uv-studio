from __future__ import annotations

import shutil
import subprocess
import tempfile
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


class LongTimelineRealMediaTests(unittest.TestCase):
    @staticmethod
    def _offer() -> CapabilityOffer:
        return CapabilityOffer(
            "local_ffmpeg.video_extract_range",
            "video.extract_range",
            "local_ffmpeg",
            "Extract range",
            OfferAvailability.AVAILABLE,
            "real-media long-timeline evidence",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    def test_ten_minute_low_resolution_source_seeks_near_end_through_product_adapter(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            self.skipTest("FFmpeg/FFprobe are not provisioned for real-media evidence")

        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Ten minute timeline")
            source = store.project_directory(project.project_id) / "sources" / "long.mp4"
            generated = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=160x90:rate=2",
                    "-t",
                    "600",
                    "-an",
                    "-c:v",
                    "mpeg4",
                    "-q:v",
                    "18",
                    "-g",
                    "20",
                    "-y",
                    str(source),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
                shell=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            self.assertGreater(source.stat().st_size, 0)

            adapter = LocalFFmpegAdapter(
                store,
                tool_paths={"ffmpeg": ffmpeg, "ffprobe": ffprobe},
                probe_timeout_sec=30,
                extract_timeout_sec=90,
            )
            result = adapter.execute(
                project_id=project.project_id,
                offer=self._offer(),
                payload={
                    "source_path": "sources/long.mp4",
                    "start_us": 598_000_000,
                    "end_us": 600_000_000,
                    "context_before_us": 1_000_000,
                },
            )

            self.assertEqual(result.output["range"]["requested"]["start_us"], 598_000_000)
            self.assertEqual(result.output["range"]["requested"]["end_us"], 600_000_000)
            self.assertEqual(result.output["range"]["context"]["start_us"], 597_000_000)
            self.assertEqual(result.output["range"]["context"]["end_us"], 600_000_000)
            self.assertEqual(len(store.load_project(project.project_id).artifacts), 2)


if __name__ == "__main__":
    unittest.main()
