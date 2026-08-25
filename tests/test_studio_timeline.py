from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from uv_studio.editor.timeline_commands import (
    AddClipCommand,
    CreateTrackCommand,
    MoveClipCommand,
    RemoveClipCommand,
    TimelineCommandError,
    TimelineCommandService,
    TrimClipCommand,
)
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.timeline import MAIN_TIMELINE_PATH, TimelineStore


class StudioTimelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        project = self.store.create_project(recipe_id="general_video", title="Studio v2")
        self.project_id = project.project_id

        video_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_video.mp4",
            allowed_roots=("sources",),
        )
        video_path.write_bytes(b"video")
        image_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_image.png",
            allowed_roots=("sources",),
        )
        image_path.write_bytes(b"image")
        audio_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_audio.wav",
            allowed_roots=("sources",),
        )
        audio_path.write_bytes(b"audio")

        self.video = ProjectReference(
            id="src_video",
            kind="video",
            path="sources/src_video.mp4",
            metadata={"duration_us": 20_000_000, "width": 1920, "height": 1080},
        )
        self.image = ProjectReference(
            id="src_image",
            kind="image",
            path="sources/src_image.png",
            metadata={"width": 1024, "height": 1024},
        )
        self.audio = ProjectReference(
            id="src_audio",
            kind="audio",
            path="sources/src_audio.wav",
            metadata={"duration_us": 30_000_000},
        )
        self.store.update_project(
            self.project_id,
            sources=(self.video, self.image, self.audio),
        )
        self.service = TimelineCommandService(self.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_multitrack_state_round_trips_through_project_store(self) -> None:
        video_track = self.service.create_track(
            self.project_id,
            CreateTrackCommand(kind="video", track_id="trk_video"),
        )
        self.assertEqual(video_track.track_id, "trk_video")
        audio_track = self.service.create_track(
            self.project_id,
            CreateTrackCommand(kind="audio", track_id="trk_audio"),
        )
        self.assertEqual(audio_track.track_id, "trk_audio")

        first = self.service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id=self.video.id,
                timeline_start_us=0,
                source_start_us=2_000_000,
                duration_us=5_000_000,
                clip_id="clip_video",
            ),
        )
        self.assertEqual(first.clip_id, "clip_video")
        self.service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id=self.image.id,
                timeline_start_us=5_000_000,
                duration_us=3_000_000,
                clip_id="clip_image",
            ),
        )
        self.service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_audio",
                reference_id=self.audio.id,
                timeline_start_us=0,
                duration_us=8_000_000,
                clip_id="clip_audio",
            ),
        )

        path = self.store.resolve_project_file(
            self.project_id,
            MAIN_TIMELINE_PATH,
            must_exist=True,
            allowed_roots=("timeline",),
        )
        self.assertTrue(path.is_file())

        reloaded = TimelineStore(ProjectStore(self.store.root)).load(
            self.project_id,
            validate_references=True,
        )
        self.assertEqual([track.track_id for track in reloaded.tracks], ["trk_video", "trk_audio"])
        self.assertEqual(
            [clip.clip_id for clip in reloaded.track("trk_video").clips],
            ["clip_video", "clip_image"],
        )
        self.assertEqual(reloaded.track("trk_audio").clips[0].reference_id, self.audio.id)

    def test_move_trim_and_remove_use_same_canonical_command_service(self) -> None:
        self.service.create_track(
            self.project_id,
            CreateTrackCommand(kind="video", track_id="trk_video"),
        )
        self.service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id=self.video.id,
                timeline_start_us=0,
                duration_us=4_000_000,
                clip_id="clip_a",
            ),
        )
        self.service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id=self.video.id,
                timeline_start_us=8_000_000,
                source_start_us=8_000_000,
                duration_us=4_000_000,
                clip_id="clip_b",
            ),
        )

        moved = self.service.move_clip(
            self.project_id,
            MoveClipCommand(clip_id="clip_b", timeline_start_us=6_000_000),
        )
        self.assertEqual(moved.timeline.locate_clip("clip_b")[1].timeline_start_us, 6_000_000)

        trimmed = self.service.trim_clip(
            self.project_id,
            TrimClipCommand(clip_id="clip_a", source_start_us=1_000_000, duration_us=3_000_000),
        )
        clip_a = trimmed.timeline.locate_clip("clip_a")[1]
        self.assertEqual(clip_a.source_start_us, 1_000_000)
        self.assertEqual(clip_a.duration_us, 3_000_000)

        removed = self.service.remove_clip(
            self.project_id,
            RemoveClipCommand(clip_id="clip_a"),
        )
        with self.assertRaises(Exception):
            removed.timeline.locate_clip("clip_a")
        self.assertEqual(
            [clip.clip_id for clip in removed.timeline.track("trk_video").clips],
            ["clip_b"],
        )

    def test_track_overlap_and_source_bounds_fail_closed(self) -> None:
        self.service.create_track(
            self.project_id,
            CreateTrackCommand(kind="video", track_id="trk_video"),
        )
        self.service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id=self.video.id,
                timeline_start_us=0,
                duration_us=5_000_000,
                clip_id="clip_a",
            ),
        )
        with self.assertRaisesRegex(TimelineCommandError, "must not overlap"):
            self.service.add_clip(
                self.project_id,
                AddClipCommand(
                    track_id="trk_video",
                    reference_id=self.image.id,
                    timeline_start_us=4_000_000,
                    duration_us=2_000_000,
                    clip_id="clip_overlap",
                ),
            )
        with self.assertRaisesRegex(TimelineCommandError, "exceeds source duration"):
            self.service.add_clip(
                self.project_id,
                AddClipCommand(
                    track_id="trk_video",
                    reference_id=self.video.id,
                    timeline_start_us=10_000_000,
                    source_start_us=19_000_000,
                    duration_us=2_000_000,
                    clip_id="clip_oob",
                ),
            )

    def test_track_kind_rejects_wrong_media_reference(self) -> None:
        self.service.create_track(
            self.project_id,
            CreateTrackCommand(kind="audio", track_id="trk_audio"),
        )
        with self.assertRaisesRegex(TimelineCommandError, "requires audio references"):
            self.service.add_clip(
                self.project_id,
                AddClipCommand(
                    track_id="trk_audio",
                    reference_id=self.video.id,
                    timeline_start_us=0,
                    duration_us=2_000_000,
                    clip_id="clip_wrong_kind",
                ),
            )

    def test_parallel_commands_do_not_lose_timeline_updates(self) -> None:
        workers = 12
        start = threading.Barrier(workers)

        def create(index: int) -> str:
            start.wait()
            result = self.service.create_track(
                self.project_id,
                CreateTrackCommand(kind="video", track_id=f"trk_parallel_{index}"),
            )
            return result.transaction_id

        with ThreadPoolExecutor(max_workers=workers) as executor:
            transaction_ids = list(executor.map(create, range(workers)))

        timeline = TimelineStore(self.store).load(self.project_id)
        self.assertEqual(
            {track.track_id for track in timeline.tracks},
            {f"trk_parallel_{index}" for index in range(workers)},
        )
        self.assertEqual(len(set(transaction_ids)), workers)


if __name__ == "__main__":
    unittest.main()
