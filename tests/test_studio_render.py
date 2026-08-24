from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.editor.studio_render import StudioRenderError, StudioTimelineRenderService
from uv_studio.editor.timeline_commands import AddClipCommand, CreateTrackCommand, TimelineCommandService
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class _FakeFFmpeg:
    def __init__(self, store: ProjectStore, *, duration_us: int, has_audio: bool = False) -> None:
        self.store = store
        self.assemble_timeout_sec = 10
        self.duration_us = duration_us
        self.has_audio = has_audio
        self.invocations: list[list[str]] = []

    def _tool(self, name: str) -> str:
        return name

    def _invoke(self, command: list[str], *, timeout: int, tool: str):
        self.invocations.append(command)
        output = Path(command[-1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-rendered-media")
        return None

    def _probe_path(self, *, canonical_path: str, source: Path) -> dict:
        return {
            "path": canonical_path,
            "duration_us": self.duration_us,
            "has_video": True,
            "has_audio": self.has_audio,
        }


class StudioTimelineRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        project = self.store.create_project(title="Studio Render")
        self.project_id = project.project_id

        first_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_a.mp4",
            allowed_roots=("sources",),
        )
        first_path.write_bytes(b"video-a")
        second_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_b.mp4",
            allowed_roots=("sources",),
        )
        second_path.write_bytes(b"video-b")
        refs = (
            ProjectReference(
                id="src_a",
                kind="video",
                path="sources/src_a.mp4",
                metadata={
                    "duration_us": 10_000_000,
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "30/1",
                },
            ),
            ProjectReference(
                id="src_b",
                kind="video",
                path="sources/src_b.mp4",
                metadata={
                    "duration_us": 10_000_000,
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "30/1",
                },
            ),
        )
        self.store.update_project(self.project_id, sources=refs)
        self.commands = TimelineCommandService(self.store)
        self.commands.create_track(
            self.project_id,
            CreateTrackCommand(kind="video", track_id="trk_video"),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_render_registers_export_bound_to_exact_timeline_revision(self) -> None:
        self.commands.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id="src_a",
                timeline_start_us=0,
                source_start_us=1_000_000,
                duration_us=3_000_000,
                clip_id="clip_a",
            ),
        )
        self.commands.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id="src_b",
                timeline_start_us=3_000_000,
                source_start_us=2_000_000,
                duration_us=2_000_000,
                clip_id="clip_b",
            ),
        )
        ffmpeg = _FakeFFmpeg(self.store, duration_us=5_000_000)
        result = StudioTimelineRenderService(self.store, ffmpeg).render(self.project_id)  # type: ignore[arg-type]

        self.assertEqual(result.video_track_id, "trk_video")
        self.assertIsNone(result.audio_track_id)
        self.assertEqual(result.duration_us, 5_000_000)
        self.assertEqual(len(result.timeline_revision_sha256), 64)
        self.assertEqual(result.artifact.kind, "video")
        self.assertTrue(result.artifact.path.startswith("exports/art_"))
        output = self.store.resolve_project_file(
            self.project_id,
            result.artifact.path,
            must_exist=True,
            allowed_roots=("exports",),
        )
        self.assertTrue(output.is_file())

        project = self.store.load_project(self.project_id)
        stored = next(item for item in project.artifacts if item.id == result.artifact.id)
        self.assertEqual(
            stored.metadata["timeline_revision_sha256"],
            result.timeline_revision_sha256,
        )
        self.assertEqual(stored.metadata["clip_ids"], ["clip_a", "clip_b"])
        self.assertEqual(stored.metadata["composition_mode"], "studio_v2_contiguous_visual_track")
        self.assertGreaterEqual(len(ffmpeg.invocations), 3)

    def test_render_refuses_visual_gap_before_starting_ffmpeg(self) -> None:
        self.commands.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id="src_a",
                timeline_start_us=1_000_000,
                duration_us=2_000_000,
                clip_id="clip_gap",
            ),
        )
        ffmpeg = _FakeFFmpeg(self.store, duration_us=2_000_000)
        with self.assertRaisesRegex(StudioRenderError, "without gaps"):
            StudioTimelineRenderService(self.store, ffmpeg).render(self.project_id)  # type: ignore[arg-type]
        self.assertEqual(ffmpeg.invocations, [])
        self.assertEqual(self.store.load_project(self.project_id).artifacts, ())


if __name__ == "__main__":
    unittest.main()
