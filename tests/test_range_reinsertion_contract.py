from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import CapabilityToolFailed, InvalidCapabilityInput
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.store import ProjectStore


class RangeReinsertionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Range reinsertion")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.source = self.project_dir / "sources" / "source.mkv"
        self.replacement = self.project_dir / "artifacts" / "replacement.mkv"
        self.source.write_bytes(b"source")
        self.replacement.write_bytes(b"replacement")
        self.offer = CapabilityOffer(
            "local_ffmpeg.video_replace_range",
            "video.replace_range",
            "local_ffmpeg",
            "Replace range",
            OfferAvailability.AVAILABLE,
            "test",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _probe_payload(
        *,
        duration: str,
        width: int = 1280,
        height: int = 720,
        audio: bool = True,
        audio_duration: str | None = None,
        video_count: int = 1,
        subtitle: bool = False,
        pix_fmt: str | None = None,
        sample_rate: str | None = None,
        channel_layout: str | None = None,
    ) -> dict:
        streams = [
            {
                "codec_type": "video",
                "codec_name": "ffv1",
                "width": width,
                "height": height,
                "duration": duration,
                "avg_frame_rate": "0/0",
                **({"pix_fmt": pix_fmt} if pix_fmt is not None else {}),
            }
            for _ in range(video_count)
        ]
        if audio:
            streams.append(
                {
                    "codec_type": "audio",
                    "codec_name": "flac",
                    "duration": audio_duration or duration,
                    **({"sample_rate": sample_rate} if sample_rate is not None else {}),
                    **({"channel_layout": channel_layout} if channel_layout is not None else {}),
                }
            )
        if subtitle:
            streams.append({"codec_type": "subtitle", "codec_name": "ass"})
        return {
            "format": {
                "duration": duration,
                "format_name": "matroska,webm",
                "size": "1000",
            },
            "streams": streams,
        }

    def _successful_runner(self, calls: list[tuple[list[str], dict]]):
        def runner(command, **kwargs):
            calls.append((list(command), dict(kwargs)))
            self.assertIs(kwargs["shell"], False)
            if command[0] == "fake-ffprobe":
                target = Path(command[-1])
                if target == self.source:
                    payload = self._probe_payload(duration="10.000000")
                elif target == self.replacement:
                    payload = self._probe_payload(duration="2.050000")
                else:
                    payload = self._probe_payload(duration="10.050000")
                return subprocess.CompletedProcess(
                    command, 0, stdout=json.dumps(payload), stderr=""
                )
            Path(command[-1]).write_bytes(b"composed")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        return runner

    def test_reinsertion_uses_zero_based_exact_segments_and_vfr_lossless_policy(self) -> None:
        calls: list[tuple[list[str], dict]] = []
        adapter = LocalFFmpegAdapter(
            self.store,
            runner=self._successful_runner(calls),
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        result = adapter.execute(
            project_id=self.project.project_id,
            offer=self.offer,
            payload={
                "source_path": "sources/source.mkv",
                "replacement_path": "artifacts/replacement.mkv",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
            },
        )

        ffprobe_calls = [command for command, _ in calls if command[0] == "fake-ffprobe"]
        ffmpeg_calls = [command for command, _ in calls if command[0] == "fake-ffmpeg"]
        self.assertEqual(len(ffprobe_calls), 3)
        self.assertEqual(len(ffmpeg_calls), 1)
        command = ffmpeg_calls[0]
        graph = command[command.index("-filter_complex") + 1]
        self.assertIn(
            "[0:v:0]setpts=PTS-STARTPTS,trim=start=0us:end=2000000us,setpts=PTS-STARTPTS",
            graph,
        )
        self.assertIn(
            "[0:a:0]asetpts=PTS-STARTPTS,atrim=start=0us:end=2000000us,asetpts=PTS-STARTPTS",
            graph,
        )
        self.assertIn("[1:v:0]setpts=PTS-STARTPTS", graph)
        self.assertIn("[1:a:0]asetpts=PTS-STARTPTS", graph)
        self.assertIn(
            "[0:v:0]setpts=PTS-STARTPTS,trim=start=4000000us:end=10000000us,setpts=PTS-STARTPTS",
            graph,
        )
        self.assertIn(
            "[0:a:0]asetpts=PTS-STARTPTS,atrim=start=4000000us:end=10000000us,asetpts=PTS-STARTPTS",
            graph,
        )
        self.assertIn("concat=n=3:v=1:a=1[vout][aout]", graph)
        self.assertEqual(command[command.index("-fps_mode") + 1], "passthrough")
        self.assertEqual(command[command.index("-c:v") + 1], "ffv1")
        self.assertEqual(command[command.index("-c:a") + 1], "flac")
        self.assertNotIn("copy", command)
        self.assertTrue(command[-1].endswith(".mkv"))

        self.assertEqual(result.output["replacement_duration_delta_us"], 50_000)
        self.assertEqual(result.output["expected_output_video_duration_us"], 10_050_000)
        self.assertEqual(result.output["actual_output_video_duration_us"], 10_050_000)
        self.assertEqual(result.output["composition_mode"], "filter_concat_ffv1_flac_vfr")
        self.assertEqual(result.output["audio_policy"], "matching_presence_single_track")
        self.assertTrue(result.output["path"].startswith("artifacts/art_"))
        self.assertNotIn(str(self.project_dir), json.dumps(result.to_dict()))

        project = self.store.load_project(self.project.project_id)
        self.assertEqual(len(project.artifacts), 1)
        artifact = project.artifacts[0]
        self.assertEqual(artifact.metadata["source_path"], "sources/source.mkv")
        self.assertEqual(artifact.metadata["replacement_path"], "artifacts/replacement.mkv")
        self.assertEqual(artifact.metadata["requested_range"]["start_us"], 2_000_000)
        self.assertNotIn(str(self.project_dir), json.dumps(artifact.to_dict()))

    def test_duration_mismatch_fails_before_ffmpeg_and_does_not_retime(self) -> None:
        calls: list[list[str]] = []

        def runner(command, **kwargs):
            calls.append(list(command))
            target = Path(command[-1])
            payload = self._probe_payload(
                duration="10.000000" if target == self.source else "2.200001"
            )
            return subprocess.CompletedProcess(
                command, 0, stdout=json.dumps(payload), stderr=""
            )

        adapter = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        with self.assertRaises(InvalidCapabilityInput):
            adapter.execute(
                project_id=self.project.project_id,
                offer=self.offer,
                payload={
                    "source_path": "sources/source.mkv",
                    "replacement_path": "artifacts/replacement.mkv",
                    "start_us": 2_000_000,
                    "end_us": 4_000_000,
                },
            )
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(command[0] == "fake-ffprobe" for command in calls))
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

    def test_geometry_audio_and_unsupported_stream_contracts_fail_closed(self) -> None:
        scenarios = (
            (self._probe_payload(duration="2.0", width=640), "resolution"),
            (self._probe_payload(duration="2.0", audio=False), "audio presence"),
            (self._probe_payload(duration="2.0", subtitle=True), "unsupported stream"),
            (self._probe_payload(duration="2.0", video_count=2), "one replacement video"),
        )
        for replacement_payload, label in scenarios:
            calls: list[list[str]] = []

            def runner(command, **kwargs):
                calls.append(list(command))
                target = Path(command[-1])
                payload = (
                    self._probe_payload(duration="10.0")
                    if target == self.source
                    else replacement_payload
                )
                return subprocess.CompletedProcess(
                    command, 0, stdout=json.dumps(payload), stderr=""
                )

            with self.subTest(contract=label):
                with self.assertRaises(InvalidCapabilityInput):
                    LocalFFmpegAdapter(
                        self.store,
                        runner=runner,
                        tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
                    ).execute(
                        project_id=self.project.project_id,
                        offer=self.offer,
                        payload={
                            "source_path": "sources/source.mkv",
                            "replacement_path": "artifacts/replacement.mkv",
                            "start_us": 2_000_000,
                            "end_us": 4_000_000,
                        },
                    )
                self.assertEqual(len(calls), 2)
                self.assertTrue(all(command[0] == "fake-ffprobe" for command in calls))
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())

    def test_known_video_audio_format_mismatch_fails_before_composition(self) -> None:
        replacement_payloads = []
        pix_fmt_mismatch = self._probe_payload(duration="2.0", pix_fmt="rgb24")
        replacement_payloads.append((pix_fmt_mismatch, "pix_fmt"))
        sample_rate_mismatch = self._probe_payload(
            duration="2.0",
            pix_fmt="yuv420p",
            sample_rate="44100",
            channel_layout="stereo",
        )
        replacement_payloads.append((sample_rate_mismatch, "sample_rate"))

        for replacement_payload, label in replacement_payloads:
            calls: list[list[str]] = []

            def runner(command, **kwargs):
                calls.append(list(command))
                target = Path(command[-1])
                if target == self.source:
                    payload = self._probe_payload(
                        duration="10.0",
                        pix_fmt="yuv420p",
                        sample_rate="48000",
                        channel_layout="stereo",
                    )
                else:
                    payload = replacement_payload
                return subprocess.CompletedProcess(
                    command, 0, stdout=json.dumps(payload), stderr=""
                )

            with self.subTest(field=label):
                with self.assertRaises(InvalidCapabilityInput):
                    LocalFFmpegAdapter(
                        self.store,
                        runner=runner,
                        tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
                    ).execute(
                        project_id=self.project.project_id,
                        offer=self.offer,
                        payload={
                            "source_path": "sources/source.mkv",
                            "replacement_path": "artifacts/replacement.mkv",
                            "start_us": 2_000_000,
                            "end_us": 4_000_000,
                        },
                    )
                self.assertEqual(len(calls), 2)
                self.assertTrue(all(command[0] == "fake-ffprobe" for command in calls))

    def test_source_audio_video_duration_mismatch_fails_closed(self) -> None:
        calls: list[list[str]] = []

        def runner(command, **kwargs):
            calls.append(list(command))
            target = Path(command[-1])
            payload = (
                self._probe_payload(duration="10.0", audio_duration="9.5")
                if target == self.source
                else self._probe_payload(duration="2.0")
            )
            return subprocess.CompletedProcess(
                command, 0, stdout=json.dumps(payload), stderr=""
            )

        with self.assertRaises(InvalidCapabilityInput):
            LocalFFmpegAdapter(
                self.store,
                runner=runner,
                tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
            ).execute(
                project_id=self.project.project_id,
                offer=self.offer,
                payload={
                    "source_path": "sources/source.mkv",
                    "replacement_path": "artifacts/replacement.mkv",
                    "start_us": 2_000_000,
                    "end_us": 4_000_000,
                },
            )
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(command[0] == "fake-ffprobe" for command in calls))

    def test_caller_cannot_choose_output_or_inject_ffmpeg_and_paths_stay_project_bounded(self) -> None:
        adapter = LocalFFmpegAdapter(
            self.store,
            tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
        )
        invalid_payloads = (
            {
                "source_path": "sources/source.mkv",
                "replacement_path": "artifacts/replacement.mkv",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
                "output_path": "artifacts/chosen.mkv",
            },
            {
                "source_path": "sources/source.mkv",
                "replacement_path": "artifacts/replacement.mkv",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
                "ffmpeg_args": ["-c", "copy"],
            },
            {
                "source_path": "../outside.mkv",
                "replacement_path": "artifacts/replacement.mkv",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
            },
            {
                "source_path": "sources/source.mkv",
                "replacement_path": "C:\\outside.mkv",
                "start_us": 2_000_000,
                "end_us": 4_000_000,
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(InvalidCapabilityInput):
                    adapter.execute(
                        project_id=self.project.project_id,
                        offer=self.offer,
                        payload=payload,
                    )

    def test_failed_or_invalid_final_output_is_removed_and_not_registered(self) -> None:
        for failure_mode in ("ffmpeg", "invalid_probe"):
            calls: list[list[str]] = []

            def runner(command, **kwargs):
                calls.append(list(command))
                if command[0] == "fake-ffprobe":
                    target = Path(command[-1])
                    if target == self.source:
                        payload = self._probe_payload(duration="10.0")
                    elif target == self.replacement:
                        payload = self._probe_payload(duration="2.0")
                    else:
                        payload = self._probe_payload(
                            duration="20.0" if failure_mode == "invalid_probe" else "10.0"
                        )
                    return subprocess.CompletedProcess(
                        command, 0, stdout=json.dumps(payload), stderr=""
                    )
                Path(command[-1]).write_bytes(b"partial")
                return subprocess.CompletedProcess(
                    command,
                    1 if failure_mode == "ffmpeg" else 0,
                    stdout="",
                    stderr="composition failed" if failure_mode == "ffmpeg" else "",
                )

            with self.subTest(failure_mode=failure_mode):
                with self.assertRaises(CapabilityToolFailed):
                    LocalFFmpegAdapter(
                        self.store,
                        runner=runner,
                        tool_paths={"ffprobe": "fake-ffprobe", "ffmpeg": "fake-ffmpeg"},
                    ).execute(
                        project_id=self.project.project_id,
                        offer=self.offer,
                        payload={
                            "source_path": "sources/source.mkv",
                            "replacement_path": "artifacts/replacement.mkv",
                            "start_us": 2_000_000,
                            "end_us": 4_000_000,
                        },
                    )
                generated = [
                    item
                    for item in (self.project_dir / "artifacts").iterdir()
                    if item.name != "replacement.mkv"
                ]
                self.assertEqual(generated, [])
                self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())


if __name__ == "__main__":
    unittest.main()
