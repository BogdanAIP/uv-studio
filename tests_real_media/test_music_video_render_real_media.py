from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capability_execution import get_local_ffmpeg_adapter
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.projects.music_assembly import MusicAssemblyStore, MusicVisualAssignment
from uv_studio.projects.music_direction import MusicDirectionStore, MusicShotPlan
from uv_studio.projects.music_map import MusicExcerpt, MusicMapStore, MusicSection, MusicTimingMarker
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe required")
class MusicVideoRenderRealMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root / "projects")
        app.dependency_overrides[get_project_store] = lambda: self.store
        self.client = TestClient(app)
        self.project_id = self.store.create_project(
            title="Real Music Video render",
            recipe_id="music_video",
        ).project_id
        self.clip_a = self._create_video("red-clip.mkv", "red", 440)
        self.clip_b = self._create_video("blue-clip.mkv", "blue", 660)
        self.song = self._create_song("master-song.wav", 880)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    @staticmethod
    def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
        completed = subprocess.run(command, capture_output=True, check=False)
        if completed.returncode != 0:
            raise AssertionError(
                f"command failed ({completed.returncode}): {command!r}\n"
                f"{completed.stderr.decode('utf-8', errors='replace')}"
            )
        return completed

    def _create_video(self, filename: str, color: str, frequency: int):
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project_id, filename)
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
                f"color=c={color}:s=320x180:r=24:d=4",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={frequency}:sample_rate=48000:duration=4",
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
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": filename,
                "content_type": "video/x-matroska",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 4_000_000,
                "has_audio": True,
                "width": 320,
                "height": 180,
            },
        )
        return next(item for item in project.sources if item.id == allocation.source_id)

    def _create_song(self, filename: str, frequency: int):
        media = ProjectSourceMediaStore(self.store)
        allocation = media.allocate(self.project_id, filename)
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
                f"sine=frequency={frequency}:sample_rate=48000:duration=6",
                "-c:a",
                "pcm_s16le",
                str(allocation.absolute_path),
            ]
        )
        body = allocation.absolute_path.read_bytes()
        project = media.register(
            self.project_id,
            allocation,
            metadata={
                "original_name": filename,
                "content_type": "audio/wav",
                "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "duration_us": 6_000_000,
                "has_audio": True,
            },
            media_kind="audio",
        )
        return next(item for item in project.sources if item.id == allocation.source_id)

    def _prepare_assembly(self, *, boundary_us: int = 3_000_000):
        music_map = MusicMapStore(self.store).set_map(
            self.project_id,
            song_reference_id=self.song.id,
            excerpt=MusicExcerpt(start_us=1_000_000, end_us=5_000_000),
            sections=(MusicSection("whole", "other", "Whole", 1_000_000, 5_000_000),),
            markers=(MusicTimingMarker("cut", "cut_point", 3_000_000),),
        )
        direction = MusicDirectionStore(self.store).set_direction(
            self.project_id,
            music_map_revision_sha256=music_map.revision_sha256,
            shots=(
                MusicShotPlan("red", 0, 1_000_000, boundary_us, "Red visual", ("cut",)),
                MusicShotPlan("blue", 1, boundary_us, 5_000_000, "Blue visual"),
            ),
        )
        return MusicAssemblyStore(self.store).set_assembly(
            self.project_id,
            music_direction_revision_sha256=direction.revision_sha256,
            assignments=(
                MusicVisualAssignment("red", self.clip_a.id, 0),
                MusicVisualAssignment("blue", self.clip_b.id, 0),
            ),
        )

    def _frequency_hz(self, media: Path, *, start: float, duration: float = 0.5) -> float:
        wav = self.root / f"freq-{start:.2f}.wav"
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
        samples = [
            int.from_bytes(frames[index : index + 2], "little", signed=True)
            for index in range(0, len(frames), 2)
        ]
        crossings = 0
        previous = samples[0]
        for current in samples[1:]:
            if (previous < 0 <= current) or (previous >= 0 > current):
                crossings += 1
            previous = current
        return crossings / (2.0 * (len(samples) / rate))

    def _rgb_at(self, media: Path, *, time_sec: float) -> tuple[int, int, int]:
        completed = self._run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{time_sec:.3f}",
                "-i",
                str(media),
                "-frames:v",
                "1",
                "-vf",
                "scale=1:1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
            ]
        )
        self.assertGreaterEqual(len(completed.stdout), 3)
        return tuple(completed.stdout[:3])  # type: ignore[return-value]

    def test_render_uses_assembly_visual_order_and_master_song_as_only_audio(self) -> None:
        assembly = self._prepare_assembly()
        rendered = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/video.render_music_video/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {"assembly_revision_sha256": assembly.revision_sha256},
            },
        )
        self.assertEqual(rendered.status_code, 200, rendered.text)
        result = rendered.json()["result"]
        output = result["output"]
        self.assertEqual(output["music_assembly_revision_sha256"], assembly.revision_sha256)
        self.assertEqual(output["song_reference_id"], self.song.id)
        self.assertEqual(output["visual_shot_ids"], ["red", "blue"])
        self.assertLess(abs(output["actual_output_video_duration_us"] - 4_000_000), 180_000)
        self.assertLess(abs(output["actual_output_audio_duration_us"] - 4_000_000), 180_000)

        path = self.store.resolve_project_file(
            self.project_id,
            output["path"],
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        red = self._rgb_at(path, time_sec=0.75)
        blue = self._rgb_at(path, time_sec=3.25)
        self.assertGreater(red[0], red[2] + 80)
        self.assertGreater(blue[2], blue[0] + 80)

        master_hz = self._frequency_hz(path, start=0.75)
        second_shot_hz = self._frequency_hz(path, start=3.0)
        self.assertAlmostEqual(master_hz, 880.0, delta=20.0)
        self.assertAlmostEqual(second_shot_hz, 880.0, delta=20.0)
        self.assertGreater(abs(master_hz - 440.0), 200.0)
        self.assertGreater(abs(second_shot_hz - 660.0), 150.0)

        artifact = next(
            item
            for item in self.store.load_project(self.project_id).artifacts
            if item.path == output["path"]
        )
        self.assertEqual(artifact.metadata["music_assembly_revision_sha256"], assembly.revision_sha256)
        self.assertEqual(artifact.metadata["song_sha256"], self.song.metadata["sha256"])
        self.assertEqual(artifact.metadata["lifecycle"], "music_video_render")
        self.assertEqual(artifact.metadata["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_render_rejects_stale_assembly_revision_before_ffmpeg(self) -> None:
        assembly = self._prepare_assembly()
        rendered = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/video.render_music_video/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {"assembly_revision_sha256": "0" * 64},
            },
        )
        self.assertEqual(rendered.status_code, 422, rendered.text)
        self.assertIn("stale Music Assembly revision", rendered.text)
        self.assertNotEqual(assembly.revision_sha256, "0" * 64)

    def test_render_rejects_unaligned_direction_before_ffmpeg(self) -> None:
        assembly = self._prepare_assembly(boundary_us=2_500_000)
        audit = MusicDirectionStore(self.store).rhythm_audit(self.project_id)
        self.assertFalse(audit["summary"]["all_aligned"])
        self.assertEqual(audit["summary"]["unaligned_count"], 1)

        def unexpected_runner(*_args, **_kwargs):
            raise AssertionError("FFmpeg/FFprobe must not run before the rhythm gate")

        app.dependency_overrides[get_local_ffmpeg_adapter] = lambda: LocalFFmpegAdapter(
            self.store,
            runner=unexpected_runner,
        )
        rendered = self.client.post(
            f"/api/uv/projects/{self.project_id}/capabilities/video.render_music_video/execute",
            json={
                "selection_policy": "local_free_first",
                "input": {"assembly_revision_sha256": assembly.revision_sha256},
            },
        )
        self.assertEqual(rendered.status_code, 422, rendered.text)
        self.assertIn("rhythm audit to be fully aligned", rendered.text)
        self.assertFalse(
            any(
                item.metadata.get("lifecycle") == "music_video_render"
                for item in self.store.load_project(self.project_id).artifacts
            )
        )


if __name__ == "__main__":
    unittest.main()
