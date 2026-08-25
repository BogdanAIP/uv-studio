from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities.adapters import WhisperCppAdapter
from uv_studio.capabilities.execution import InvalidCapabilityInput
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore


class FakeWhisperRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command, **kwargs):
        argv = [str(item) for item in command]
        self.commands.append(argv)
        executable = Path(argv[0]).name.lower()
        if "ffmpeg" in executable:
            Path(argv[-1]).write_bytes(b"RIFF" + b"\x00" * 256)
        else:
            output_prefix = Path(argv[argv.index("-of") + 1])
            output = {
                "result": {"language": "en"},
                "transcription": [
                    {
                        "timestamps": {"from": "00:00:00,000", "to": "00:00:01,250"},
                        "offsets": {"from": 0, "to": 1250},
                        "text": " Hello there ",
                    },
                    {
                        "timestamps": {"from": "00:00:01,500", "to": "00:00:02,500"},
                        "offsets": {"from": 1500, "to": 2500},
                        "text": " General Kenobi ",
                    },
                ],
            }
            output_prefix.with_suffix(".json").write_text(
                json.dumps(output), encoding="utf-8"
            )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


class WhisperCppAdapterTests(unittest.TestCase):
    def _fixture(self, root: Path):
        store = ProjectStore(root / "projects")
        project = store.create_project(recipe_id="general_video", title="ASR adapter")
        media = ProjectSourceMediaStore(store)
        allocation = media.allocate(project.project_id, "source.mp4")
        allocation.absolute_path.write_bytes(b"fake-video")
        updated = media.register(
            project.project_id,
            allocation,
            metadata={
                "sha256": "3" * 64,
                "duration_us": 9_000_000,
                "has_audio": True,
            },
        )
        source = updated.sources[0]
        runtime = root / "whisper-cli"
        model = root / "ggml.bin"
        ffmpeg = root / "ffmpeg"
        runtime.write_bytes(b"runtime")
        model.write_bytes(b"model")
        ffmpeg.write_bytes(b"ffmpeg")
        return store, project.project_id, source, runtime, model, ffmpeg

    @staticmethod
    def _offer() -> CapabilityOffer:
        return CapabilityOffer(
            offer_id="local_whisper_cpp.speech_transcribe",
            capability_id="speech.transcribe",
            adapter_id="local_whisper_cpp",
            title="whisper.cpp local transcription",
            availability=OfferAvailability.AVAILABLE,
            reason="test runtime",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
            features=("speech.timestamps",),
        )

    def test_transcription_normalizes_offsets_to_source_timeline_microseconds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, project_id, source, runtime, model, ffmpeg = self._fixture(root)
            runner = FakeWhisperRunner()
            adapter = WhisperCppAdapter(
                store,
                runner=runner,
                binary_path=runtime,
                model_path=model,
                ffmpeg_path=ffmpeg,
            )

            result = adapter.execute(
                project_id=project_id,
                offer=self._offer(),
                payload={
                    "source_id": source.id,
                    "start_us": 2_000_000,
                    "end_us": 5_000_000,
                    "language": "auto",
                },
            )

            output = result.output
            self.assertEqual(output["source_id"], source.id)
            self.assertEqual(output["source_sha256"], "3" * 64)
            self.assertEqual(output["language"], "en")
            self.assertEqual(output["start_us"], 2_000_000)
            self.assertEqual(output["end_us"], 5_000_000)
            self.assertEqual(
                [
                    (item["start_us"], item["end_us"], item["text"])
                    for item in output["segments"]
                ],
                [
                    (2_000_000, 3_250_000, "Hello there"),
                    (3_500_000, 4_500_000, "General Kenobi"),
                ],
            )
            self.assertEqual(len(runner.commands), 2)
            ffmpeg_argv, whisper_argv = runner.commands
            self.assertIn("-ss", ffmpeg_argv)
            self.assertIn("2000000us", ffmpeg_argv)
            self.assertIn("-t", ffmpeg_argv)
            self.assertIn("3000000us", ffmpeg_argv)
            self.assertIn("-ojf", whisper_argv)
            self.assertEqual(whisper_argv[whisper_argv.index("-l") + 1], "auto")
            self.assertNotIn(str(runtime), json.dumps(output))
            self.assertNotIn(str(model), json.dumps(output))
            self.assertNotIn(str(ffmpeg), json.dumps(output))

    def test_full_source_range_is_used_when_range_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, project_id, source, runtime, model, ffmpeg = self._fixture(root)
            runner = FakeWhisperRunner()
            result = WhisperCppAdapter(
                store,
                runner=runner,
                binary_path=runtime,
                model_path=model,
                ffmpeg_path=ffmpeg,
            ).execute(
                project_id=project_id,
                offer=self._offer(),
                payload={"source_id": source.id, "language": "en-US"},
            )
            self.assertEqual(result.output["start_us"], 0)
            self.assertEqual(result.output["end_us"], 9_000_000)
            whisper_argv = runner.commands[1]
            self.assertEqual(whisper_argv[whisper_argv.index("-l") + 1], "en-us")

    def test_raw_paths_and_runtime_controls_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, project_id, source, runtime, model, ffmpeg = self._fixture(root)
            adapter = WhisperCppAdapter(
                store,
                runner=FakeWhisperRunner(),
                binary_path=runtime,
                model_path=model,
                ffmpeg_path=ffmpeg,
            )
            for forbidden in ("source_path", "model_path", "flags", "output_path"):
                with self.subTest(forbidden=forbidden), self.assertRaises(InvalidCapabilityInput):
                    adapter.execute(
                        project_id=project_id,
                        offer=self._offer(),
                        payload={"source_id": source.id, forbidden: "attacker-controlled"},
                    )

    def test_unknown_source_is_invalid_capability_input_before_runtime_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, project_id, source, runtime, model, ffmpeg = self._fixture(root)
            runner = FakeWhisperRunner()
            adapter = WhisperCppAdapter(
                store,
                runner=runner,
                binary_path=runtime,
                model_path=model,
                ffmpeg_path=ffmpeg,
            )
            with self.assertRaises(InvalidCapabilityInput):
                adapter.execute(
                    project_id=project_id,
                    offer=self._offer(),
                    payload={"source_id": "src_missing"},
                )
            self.assertEqual(runner.commands, [])

    def test_partial_or_out_of_bounds_ranges_are_rejected_before_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, project_id, source, runtime, model, ffmpeg = self._fixture(root)
            runner = FakeWhisperRunner()
            adapter = WhisperCppAdapter(
                store,
                runner=runner,
                binary_path=runtime,
                model_path=model,
                ffmpeg_path=ffmpeg,
            )
            with self.assertRaises(InvalidCapabilityInput):
                adapter.execute(
                    project_id=project_id,
                    offer=self._offer(),
                    payload={"source_id": source.id, "start_us": 1_000_000},
                )
            with self.assertRaises(InvalidCapabilityInput):
                adapter.execute(
                    project_id=project_id,
                    offer=self._offer(),
                    payload={"source_id": source.id, "start_us": 8_000_000, "end_us": 10_000_000},
                )
            self.assertEqual(runner.commands, [])


if __name__ == "__main__":
    unittest.main()
