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
        self.project = self.store.create_project(recipe_id="general_video", title="Local media")
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

    @staticmethod
    def _probe_payload(
        *,
        duration: str = "12.500001",
        video: bool = True,
        audio: bool = True,
    ) -> dict:
        streams = []
        if video:
            streams.append(
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "30/1",
                }
            )
        if audio:
            streams.append({"codec_type": "audio", "codec_name": "aac"})
        return {
            "format": {
                "duration": duration,
                "format_name": "mov,mp4",
                "size": "1234",
            },
            "streams": streams,
        }

    def test_probe_uses_argv_without_shell_and_returns_structured_exact_duration(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"not-real-media")
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(self._probe_payload(duration="3.500001")),
                stderr="",
            )

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

        self.assertEqual(result.output["duration_sec"], 3.500001)
        self.assertEqual(result.output["duration_us"], 3_500_001)
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

    def test_range_extract_probes_duration_and_creates_lossless_requested_and_context_artifacts(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"source")
        calls = []

        def runner(command, **kwargs):
            calls.append((list(command), dict(kwargs)))
            self.assertIs(kwargs["shell"], False)
            if command[0] == "fake-ffprobe":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(self._probe_payload()),
                    stderr="",
                )
            output = Path(command[-1])
            output.write_bytes(f"generated-{len(calls)}".encode("utf-8"))
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        result = adapter.execute(
            project_id=self.project.project_id,
            offer=self._offer("video.extract_range", "local_ffmpeg.video_extract_range"),
            payload={
                "source_path": "sources/clip.mp4",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
                "context_before_us": 3_000_000,
                "context_after_us": 10_000_000,
            },
        )

        ffprobe_calls = [item[0] for item in calls if item[0][0] == "fake-ffprobe"]
        ffmpeg_calls = [item[0] for item in calls if item[0][0] == "fake-ffmpeg"]
        self.assertEqual(len(ffprobe_calls), 4)
        self.assertEqual(len(ffmpeg_calls), 3)
        expected_segments = (
            ("0us", "2000000us"),
            ("2000000us", "2000000us"),
            ("4000000us", "8500001us"),
        )
        for command, (expected_ss, expected_t) in zip(ffmpeg_calls, expected_segments):
            self.assertEqual(command[0], "fake-ffmpeg")
            self.assertEqual(command[command.index("-ss") + 1], expected_ss)
            self.assertEqual(command[command.index("-t") + 1], expected_t)
            self.assertEqual(command[command.index("-c:v") + 1], "ffv1")
            self.assertEqual(command[command.index("-c:a") + 1], "flac")
            self.assertNotIn("copy", command)
            self.assertTrue(command[-1].endswith(".mkv"))

        self.assertEqual(result.output["source_path"], "sources/clip.mp4")
        self.assertEqual(result.output["range"]["requested"]["start_us"], 2_000_000)
        self.assertEqual(result.output["range"]["requested"]["end_us"], 4_000_000)
        self.assertEqual(result.output["range"]["context"]["start_us"], 0)
        self.assertEqual(result.output["range"]["context"]["end_us"], 12_500_001)
        self.assertTrue(result.output["requested_path"].startswith("artifacts/art_"))
        self.assertTrue(result.output["context_before_path"].startswith("artifacts/art_"))
        self.assertTrue(result.output["context_after_path"].startswith("artifacts/art_"))
        self.assertEqual(result.output["extraction_mode"], "accurate_seek_lossless_ffv1_flac")
        self.assertNotIn(str(self.project_dir), json.dumps(result.to_dict()))

        reloaded = self.store.load_project(self.project.project_id)
        self.assertEqual(len(reloaded.artifacts), 3)
        roles = [artifact.metadata["range_role"] for artifact in reloaded.artifacts]
        self.assertEqual(roles, ["context_before", "requested", "context_after"])
        for artifact in reloaded.artifacts:
            self.assertEqual(artifact.metadata["source_path"], "sources/clip.mp4")
            self.assertEqual(
                artifact.metadata["extraction_mode"],
                "accurate_seek_lossless_ffv1_flac",
            )
            self.assertNotIn(str(self.project_dir), json.dumps(artifact.to_dict()))
            self.assertGreater(
                self.store.resolve_project_file(
                    self.project.project_id,
                    artifact.path,
                    must_exist=True,
                    allowed_roots=("artifacts",),
                ).stat().st_size,
                0,
            )

    def test_range_extract_without_context_creates_only_requested_artifact(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"source")
        ffmpeg_calls = []

        def runner(command, **kwargs):
            if command[0] == "fake-ffprobe":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(self._probe_payload(duration="5.0", audio=False)),
                    stderr="",
                )
            ffmpeg_calls.append(command)
            Path(command[-1]).write_bytes(b"range")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        result = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        ).execute(
            project_id=self.project.project_id,
            offer=self._offer("video.extract_range", "local_ffmpeg.video_extract_range"),
            payload={
                "source_path": "sources/clip.mp4",
                "start_us": 1_000_000,
                "end_us": 2_000_000,
            },
        )
        self.assertEqual(len(ffmpeg_calls), 1)
        self.assertIsNone(result.output["context_before_path"])
        self.assertIsNone(result.output["context_after_path"])
        self.assertEqual(len(self.store.load_project(self.project.project_id).artifacts), 1)

    def test_range_extract_rejects_out_of_duration_and_non_video_sources_before_ffmpeg(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"source")
        for video, end_us in ((True, 6_000_000), (False, 2_000_000)):
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(self._probe_payload(duration="5.0", video=video)),
                    stderr="",
                )

            adapter = LocalFFmpegAdapter(
                self.store,
                runner=runner,
                tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
            )
            with self.subTest(video=video, end_us=end_us):
                with self.assertRaises(InvalidCapabilityInput):
                    adapter.execute(
                        project_id=self.project.project_id,
                        offer=self._offer(
                            "video.extract_range",
                            "local_ffmpeg.video_extract_range",
                        ),
                        payload={
                            "source_path": "sources/clip.mp4",
                            "start_us": 1_000_000,
                            "end_us": end_us,
                        },
                    )
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][0], "fake-ffprobe")
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

    def test_range_extract_rejects_raw_options_output_path_and_traversal(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"source")
        adapter = LocalFFmpegAdapter(
            self.store,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        invalid_payloads = (
            {
                "source_path": "sources/clip.mp4",
                "start_us": 0,
                "end_us": 1,
                "output_path": "artifacts/chosen.mkv",
            },
            {
                "source_path": "sources/clip.mp4",
                "start_us": 0,
                "end_us": 1,
                "ffmpeg_args": ["-c", "copy"],
            },
            {
                "source_path": "../outside.mp4",
                "start_us": 0,
                "end_us": 1,
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(InvalidCapabilityInput):
                    adapter.execute(
                        project_id=self.project.project_id,
                        offer=self._offer(
                            "video.extract_range",
                            "local_ffmpeg.video_extract_range",
                        ),
                        payload=payload,
                    )

    def test_range_extract_failure_removes_all_partial_outputs_and_registers_nothing(self) -> None:
        source = self.project_dir / "sources" / "clip.mp4"
        source.write_bytes(b"source")
        ffmpeg_count = 0

        def runner(command, **kwargs):
            nonlocal ffmpeg_count
            if command[0] == "fake-ffprobe":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(self._probe_payload(duration="10.0")),
                    stderr="",
                )
            ffmpeg_count += 1
            Path(command[-1]).write_bytes(b"partial")
            if ffmpeg_count == 2:
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="simulated cut failure")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        with self.assertRaises(CapabilityToolFailed):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self._offer("video.extract_range", "local_ffmpeg.video_extract_range"),
                payload={
                    "source_path": "sources/clip.mp4",
                    "start_us": 2_000_000,
                    "end_us": 4_000_000,
                    "context_before_us": 1_000_000,
                    "context_after_us": 1_000_000,
                },
            )
        self.assertEqual(ffmpeg_count, 2)
        self.assertEqual(list((self.project_dir / "artifacts").iterdir()), [])
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

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
