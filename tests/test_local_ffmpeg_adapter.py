from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import (
    CapabilityToolFailed,
    InvalidCapabilityInput,
    UnsupportedCapabilityExecution,
)
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.store import ProjectStore


class LocalFFmpegAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Local media")
        self.project_dir = self.store.project_directory(self.project.project_id)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _offer(capability_id: str, offer_id: str, *, cost: CostClass = CostClass.FREE) -> CapabilityOffer:
        return CapabilityOffer(
            offer_id,
            capability_id,
            "local_ffmpeg",
            offer_id,
            OfferAvailability.AVAILABLE,
            "test",
            LocalityClass.LOCAL,
            cost,
            False,
        )

    def test_probe_uses_argv_without_shell_and_returns_structured_metadata(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"not-real-media")
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            payload = {
                "format": {"duration": "3.5", "format_name": "mov,mp4", "size": "1234"},
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 1280,
                        "height": 720,
                        "avg_frame_rate": "30/1",
                    },
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
            }
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

        adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        result = adapter.execute(
            project_id=self.project.project_id,
            offer=self._offer("media.probe", "local_ffmpeg.media_probe"),
            payload={"path": "sources/clip.mp4"},
        )

        self.assertEqual(result.output["duration_sec"], 3.5)
        self.assertTrue(result.output["has_video"])
        self.assertTrue(result.output["has_audio"])
        self.assertEqual(result.output["video"]["width"], 1280)
        self.assertEqual(calls[0][0][0], "fake-ffprobe")
        self.assertIs(calls[0][1]["shell"], False)
        self.assertEqual(result.artifact, None)

    def test_probe_rejects_path_traversal(self) -> None:
        adapter = LocalFFmpegAdapter(
            self.store,
            tool_paths={"ffprobe": "fake-ffprobe"},
        )
        with self.assertRaises(InvalidCapabilityInput):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self._offer("media.probe", "local_ffmpeg.media_probe"),
                payload={"path": "../outside.mp4"},
            )

    def test_concat_registers_artifact_only_after_success(self) -> None:
        for name in ("a.mp4", "b.mp4"):
            (self.project_dir / "sources" / name).write_bytes(name.encode("utf-8"))
        observed_manifest = {"text": None}

        def runner(command, **kwargs):
            self.assertIs(kwargs["shell"], False)
            manifest = Path(command[command.index("-i") + 1])
            observed_manifest["text"] = manifest.read_text(encoding="utf-8")
            output = Path(command[-1])
            output.write_bytes(b"joined")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffmpeg": "fake-ffmpeg", "ffprobe": "fake-ffprobe"},
        )
        result = adapter.execute(
            project_id=self.project.project_id,
            offer=self._offer("timeline.assemble", "local_ffmpeg.timeline_assemble"),
            payload={
                "input_paths": ["sources/a.mp4", "sources/b.mp4"],
                "output_path": "artifacts/joined.mp4",
            },
        )

        self.assertTrue((self.project_dir / "artifacts" / "joined.mp4").is_file())
        self.assertIn("a.mp4", observed_manifest["text"])
        self.assertIn("b.mp4", observed_manifest["text"])
        self.assertIsNotNone(result.artifact)
        reloaded = self.store.load_project(self.project.project_id)
        self.assertEqual(len(reloaded.artifacts), 1)
        self.assertEqual(reloaded.artifacts[0].path, "artifacts/joined.mp4")

    def test_concat_failure_does_not_register_artifact(self) -> None:
        (self.project_dir / "sources" / "a.mp4").write_bytes(b"a")

        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="incompatible streams")

        adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffmpeg": "fake-ffmpeg"},
        )
        with self.assertRaises(CapabilityToolFailed):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self._offer("timeline.assemble", "local_ffmpeg.timeline_assemble"),
                payload={
                    "input_paths": ["sources/a.mp4"],
                    "output_path": "artifacts/joined.mp4",
                },
            )
        self.assertFalse((self.project_dir / "artifacts" / "joined.mp4").exists())
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

    def test_concat_rejects_output_outside_artifact_or_export_roots(self) -> None:
        (self.project_dir / "sources" / "a.mp4").write_bytes(b"a")
        adapter = LocalFFmpegAdapter(
            self.store,
            tool_paths={"ffmpeg": "fake-ffmpeg"},
        )
        with self.assertRaises(InvalidCapabilityInput):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self._offer("timeline.assemble", "local_ffmpeg.timeline_assemble"),
                payload={
                    "input_paths": ["sources/a.mp4"],
                    "output_path": "sources/should-not-write.mp4",
                },
            )

    def test_paid_local_offer_is_rejected_even_if_pinned_elsewhere(self) -> None:
        adapter = LocalFFmpegAdapter(self.store, tool_paths={"ffprobe": "fake-ffprobe"})
        with self.assertRaises(UnsupportedCapabilityExecution):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self._offer(
                    "media.probe",
                    "local_ffmpeg.paid_probe",
                    cost=CostClass.PAID,
                ),
                payload={"path": "sources/missing.mp4"},
            )

    def test_timeout_is_reported_as_tool_failure(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"x")

        def runner(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe"},
            probe_timeout_sec=1,
        )
        with self.assertRaises(CapabilityToolFailed):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self._offer("media.probe", "local_ffmpeg.media_probe"),
                payload={"path": "sources/clip.mp4"},
            )


if __name__ == "__main__":
    unittest.main()
