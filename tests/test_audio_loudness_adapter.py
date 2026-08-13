from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities import OfferAvailability, build_builtin_capability_registry
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.execution import InvalidCapabilityInput
from uv_studio.projects.prepared_audio import ProjectPreparedAudioStore
from uv_studio.projects.store import ProjectStore


class LoudnessRunner:
    def __init__(self, *, silence: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.silence = silence

    def __call__(self, command, **kwargs):
        argv = [str(item) for item in command]
        self.commands.append(argv)
        values = (
            {
                "input_i": "-inf",
                "input_tp": "-inf",
                "input_lra": "0.00",
                "input_thresh": "-70.00",
            }
            if self.silence
            else {
                "input_i": "-20.43",
                "input_tp": "-1.27",
                "input_lra": "3.40",
                "input_thresh": "-30.55",
                "output_i": "-23.00",
            }
        )
        stderr = "ffmpeg analysis log\n{\n" + ",\n".join(
            f'  "{key}": "{value}"' for key, value in values.items()
        ) + "\n}\n"
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr=stderr)


class AudioLoudnessAdapterTests(unittest.TestCase):
    def _fixture(self, root: Path):
        store = ProjectStore(root / "projects")
        project = store.create_project(title="Loudness")
        audio_store = ProjectPreparedAudioStore(store)
        allocation = audio_store.allocate(project.project_id, "voice.wav")
        body = b"prepared-audio"
        allocation.absolute_path.write_bytes(body)
        updated = audio_store.register(
            project.project_id,
            allocation,
            metadata={
                "original_name": "voice.wav",
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 2_000_000,
                "has_audio": True,
                "has_video": False,
                "origin": "recorded",
            },
        )
        reference = next(item for item in updated.artifacts if item.id == allocation.audio_id)
        return store, project.project_id, reference

    @staticmethod
    def _offer():
        with mock.patch("uv_studio.capabilities.adapters.audio_loudness.shutil.which", return_value="ffmpeg"):
            registry = build_builtin_capability_registry()
        return registry.get_offer("local_ffmpeg.audio_measure_loudness")

    def test_measurement_returns_revision_bound_lufs_true_peak_and_lra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, reference = self._fixture(Path(tmp))
            runner = LoudnessRunner()
            result = LocalFFmpegAdapter(
                store,
                runner=runner,
                tool_paths={"ffmpeg": "ffmpeg-test"},
            ).execute(
                project_id=project_id,
                offer=self._offer(),
                payload={"audio_id": reference.id},
            )
            output = result.output
            self.assertEqual(output["audio_id"], reference.id)
            self.assertEqual(output["audio_sha256"], reference.metadata["sha256"])
            self.assertEqual(output["duration_us"], 2_000_000)
            self.assertTrue(output["measurable"])
            self.assertAlmostEqual(output["integrated_lufs"], -20.43)
            self.assertAlmostEqual(output["true_peak_dbtp"], -1.27)
            self.assertAlmostEqual(output["loudness_range_lu"], 3.40)
            self.assertAlmostEqual(output["threshold_lufs"], -30.55)
            self.assertEqual(len(runner.commands), 1)
            command = runner.commands[0]
            self.assertIn("loudnorm=I=-23:LRA=7:TP=-2:print_format=json", command)
            self.assertNotIn(str(store.root), str(output))

    def test_silence_is_reported_as_unmeasurable_instead_of_fabricating_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, reference = self._fixture(Path(tmp))
            result = LocalFFmpegAdapter(
                store,
                runner=LoudnessRunner(silence=True),
                tool_paths={"ffmpeg": "ffmpeg-test"},
            ).execute(
                project_id=project_id,
                offer=self._offer(),
                payload={"audio_id": reference.id},
            )
            self.assertFalse(result.output["measurable"])
            self.assertIsNone(result.output["integrated_lufs"])
            self.assertIsNone(result.output["true_peak_dbtp"])
            self.assertEqual(result.output["loudness_range_lu"], 0.0)

    def test_caller_cannot_supply_audio_path_or_ffmpeg_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, reference = self._fixture(Path(tmp))
            adapter = LocalFFmpegAdapter(
                store,
                runner=LoudnessRunner(),
                tool_paths={"ffmpeg": "ffmpeg-test"},
            )
            for forbidden in ("path", "filter", "target_lufs", "output_path"):
                with self.subTest(forbidden=forbidden), self.assertRaises(InvalidCapabilityInput):
                    adapter.execute(
                        project_id=project_id,
                        offer=self._offer(),
                        payload={"audio_id": reference.id, forbidden: "attacker"},
                    )

    def test_offer_is_unavailable_without_ffmpeg(self) -> None:
        with mock.patch("uv_studio.capabilities.adapters.audio_loudness.shutil.which", return_value=None):
            registry = build_builtin_capability_registry()
        offer = registry.get_offer("local_ffmpeg.audio_measure_loudness")
        self.assertEqual(offer.availability, OfferAvailability.UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
