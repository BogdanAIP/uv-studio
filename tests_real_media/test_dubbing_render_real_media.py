from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.projects import get_project_store
from uv_studio.projects.prepared_audio import ProjectPreparedAudioStore
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe required")
class DubbingRenderRealMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        self.project_id = self.store.create_project(
            title="Real dubbing render",
            recipe_id="general_video",
        ).project_id
        self.source = self._create_source()
        self.audio = self._create_prepared_speech()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _run(command: list[str]) -> None:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise AssertionError(
                f"command failed ({completed.returncode}): {command!r}\n{completed.stderr}"
            )

    def _create_source(self):
        media_store = ProjectSourceMediaStore(self.store)
        allocation = media_store.allocate(self.project_id, "source.mkv")
        self._run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=320x180:r=24:d=6",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=6",
                "-filter:a",
                "volume=0.10",
                "-shortest",
                "-c:v",
                "ffv1",
                "-level",
                "3",
                "-c:a",
                "pcm_s16le",
                str(allocation.absolute_path),
            ]
        )
        body = allocation.absolute_path.read_bytes()
        project = media_store.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "source.mkv",
                "content_type": "video/x-matroska",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 6_000_000,
                "has_audio": True,
                "width": 320,
                "height": 180,
            },
        )
        return next(item for item in project.sources if item.id == allocation.source_id)

    def _create_prepared_speech(self):
        audio_store = ProjectPreparedAudioStore(self.store)
        allocation = audio_store.allocate(self.project_id, "dub.wav")
        self._run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:sample_rate=48000:duration=1.8",
                "-filter:a",
                "volume=0.10",
                "-c:a",
                "pcm_s16le",
                str(allocation.absolute_path),
            ]
        )
        body = allocation.absolute_path.read_bytes()
        project = audio_store.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": "dub.wav",
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 1_800_000,
                "has_audio": True,
                "has_video": False,
                "origin": "recorded",
            },
        )
        return next(item for item in project.artifacts if item.id == allocation.audio_id)

    def _accept_dubbing(self) -> dict:
        transcript_response = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "import_dubbing_transcript",
                "source_id": self.source.id,
                "language": "en",
                "start_us": 1_000_000,
                "end_us": 5_000_000,
                "segments": [
                    {
                        "segment_id": "seg_real",
                        "start_us": 2_000_000,
                        "end_us": 4_000_000,
                        "text": "Real-media dubbing segment",
                    }
                ],
            },
        )
        self.assertEqual(transcript_response.status_code, 201, transcript_response.text)
        dubbing_id = transcript_response.json()["dubbing_id"]

        attached = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "attach_prepared_speech",
                "dubbing_id": dubbing_id,
                "audio_id": self.audio.id,
                "segment_id": "seg_real",
            },
        )
        self.assertEqual(attached.status_code, 201, attached.text)
        take_id = attached.json()["payload"]["prepared_speech"]["take_id"]

        reviewed = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "review_prepared_speech",
                "take_id": take_id,
                "verdict": "approved",
                "content_fidelity_confirmed": True,
                "synchronization_confirmed": True,
                "note": "Real-media render evidence",
            },
        )
        self.assertEqual(reviewed.status_code, 201, reviewed.text)
        review = reviewed.json()["payload"]["review"]
        self.assertTrue(review["audio_safety_pass"])
        self.assertTrue(review["timing_pass"])

        accepted = self.client.post(
            f"/api/uv/projects/{self.project_id}/editor/commands",
            json={
                "command": "accept_dubbing_review",
                "review_id": review["review_id"],
                "composition_policy": "replace_source_audio_range",
            },
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        return accepted.json()["payload"]["accepted_dubbing"]

    def _render(self):
        return self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/video.render_dubbing/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {"source_id": self.source.id},
            },
        )

    def _frequency_hz(self, media: Path, *, start: float, duration: float = 0.5) -> float:
        wav = self.root / f"probe-{start:.2f}.wav"
        self._run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{start:.3f}",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(media),
                "-map",
                "0:a:0",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "pcm_s16le",
                str(wav),
            ]
        )
        with wave.open(str(wav), "rb") as handle:
            frames = handle.readframes(handle.getnframes())
            rate = handle.getframerate()
        samples = [int.from_bytes(frames[index : index + 2], "little", signed=True) for index in range(0, len(frames), 2)]
        crossings = 0
        previous = samples[0]
        for current in samples[1:]:
            if (previous < 0 <= current) or (previous >= 0 > current):
                crossings += 1
            previous = current
        seconds = len(samples) / rate
        return crossings / (2.0 * seconds)

    def test_render_replaces_only_accepted_dialogue_range_and_preserves_video_duration(self) -> None:
        accepted = self._accept_dubbing()
        rendered = self._render()
        self.assertEqual(rendered.status_code, 200, rendered.text)
        result = rendered.json()["result"]
        output = result["output"]
        self.assertEqual(output["accepted_dubbing_ids"], [accepted["accepted_id"]])
        self.assertEqual(output["visual_edit_ids"], [])
        self.assertEqual(output["composition_mode"], "canonical_visual_master_then_exact_dubbing_audio_concat")
        self.assertLess(abs(output["actual_output_video_duration_us"] - 6_000_000), 100_000)
        self.assertLess(abs(output["actual_output_audio_duration_us"] - 6_000_000), 100_000)

        path = self.store.resolve_project_file(
            self.project_id,
            output["path"],
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        before_hz = self._frequency_hz(path, start=0.75)
        dubbed_hz = self._frequency_hz(path, start=2.40)
        after_hz = self._frequency_hz(path, start=4.75)
        self.assertAlmostEqual(before_hz, 440.0, delta=12.0)
        self.assertAlmostEqual(dubbed_hz, 880.0, delta=18.0)
        self.assertAlmostEqual(after_hz, 440.0, delta=12.0)

        artifact = next(
            item for item in self.store.load_project(self.project_id).artifacts if item.path == output["path"]
        )
        self.assertEqual(artifact.metadata["source_id"], self.source.id)
        self.assertEqual(artifact.metadata["accepted_dubbing_ids"], [accepted["accepted_id"]])
        self.assertEqual(artifact.metadata["mapped_ranges"][0]["source_start_us"], 2_000_000)
        self.assertEqual(artifact.metadata["mapped_ranges"][0]["master_start_us"], 2_000_000)

    def test_render_rejects_source_bytes_changed_after_accept(self) -> None:
        self._accept_dubbing()
        source_path = self.store.resolve_project_file(
            self.project_id,
            self.source.path,
            must_exist=True,
            allowed_roots=("sources",),
        )
        with source_path.open("ab") as handle:
            handle.write(b"tampered-after-accept")

        rendered = self._render()
        self.assertEqual(rendered.status_code, 422, rendered.text)
        self.assertIn("registered media size no longer matches metadata", rendered.text)

    def test_render_rejects_prepared_audio_bytes_changed_after_accept(self) -> None:
        self._accept_dubbing()
        audio_path = self.store.resolve_project_file(
            self.project_id,
            self.audio.path,
            must_exist=True,
            allowed_roots=("assets",),
        )
        with audio_path.open("ab") as handle:
            handle.write(b"tampered-after-accept")

        rendered = self._render()
        self.assertEqual(rendered.status_code, 422, rendered.text)
        self.assertIn("registered media size no longer matches metadata", rendered.text)


if __name__ == "__main__":
    unittest.main()
