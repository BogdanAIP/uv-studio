from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from uv_studio.editor.studio_mlt import StudioMLTTimelineAdapter
from uv_studio.editor.timeline_commands import AddClipCommand, CreateTrackCommand, TimelineCommandService
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class StudioMLTProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        project = self.store.create_project(recipe_id="general_video", title="MLT Studio")
        self.project_id = project.project_id

        video_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_video.mp4",
            allowed_roots=("sources",),
        )
        video_path.write_bytes(b"video")
        audio_path = self.store.resolve_project_file(
            self.project_id,
            "sources/src_audio.wav",
            allowed_roots=("sources",),
        )
        audio_path.write_bytes(b"audio")
        refs = (
            ProjectReference(
                id="src_video",
                kind="video",
                path="sources/src_video.mp4",
                metadata={
                    "duration_us": 20_000_000,
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "30/1",
                },
            ),
            ProjectReference(
                id="src_audio",
                kind="audio",
                path="sources/src_audio.wav",
                metadata={"duration_us": 20_000_000},
            ),
        )
        self.store.update_project(self.project_id, sources=refs)
        service = TimelineCommandService(self.store)
        service.create_track(
            self.project_id,
            CreateTrackCommand(kind="video", track_id="trk_video"),
        )
        service.create_track(
            self.project_id,
            CreateTrackCommand(kind="audio", track_id="trk_audio"),
        )
        service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_video",
                reference_id="src_video",
                timeline_start_us=1_000_000,
                source_start_us=2_000_000,
                duration_us=5_000_000,
                clip_id="clip_video",
            ),
        )
        service.add_clip(
            self.project_id,
            AddClipCommand(
                track_id="trk_audio",
                reference_id="src_audio",
                timeline_start_us=0,
                duration_us=6_000_000,
                clip_id="clip_audio",
            ),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_projection_is_derived_and_declares_producers_before_playlists(self) -> None:
        projection = StudioMLTTimelineAdapter(self.store).project(self.project_id)
        self.assertEqual(projection.timeline_id, "main")
        self.assertEqual((projection.frame_rate_num, projection.frame_rate_den), (30, 1))
        self.assertEqual((projection.width, projection.height), (1280, 720))
        self.assertEqual(projection.duration_us, 6_000_000)
        self.assertEqual([track.track_id for track in projection.tracks], ["trk_video", "trk_audio"])

        root = ET.fromstring(projection.xml_text)
        tags = [child.tag for child in root]
        first_playlist = tags.index("playlist")
        producer_indexes = [index for index, tag in enumerate(tags) if tag == "producer"]
        self.assertTrue(producer_indexes)
        self.assertTrue(all(index < first_playlist for index in producer_indexes))

        playlists = root.findall("playlist")
        self.assertEqual(len(playlists), 2)
        video_playlist = playlists[0]
        self.assertEqual(video_playlist[0].tag, "blank")
        self.assertEqual(video_playlist[0].attrib["length"], "30")
        video_entry = video_playlist[1]
        self.assertEqual(video_entry.attrib["uv_clip_id"], "clip_video")
        self.assertEqual(video_entry.attrib["in"], "60")
        self.assertEqual(video_entry.attrib["out"], "209")

        tractor_tracks = root.find("tractor").findall("track")  # type: ignore[union-attr]
        self.assertEqual(tractor_tracks[0].attrib["hide"], "audio")
        self.assertEqual(tractor_tracks[1].attrib["hide"], "video")

    def test_public_summary_never_exposes_resolved_host_paths(self) -> None:
        adapter = StudioMLTTimelineAdapter(self.store, melt_path="explicit-melt-command")
        summary = adapter.project_summary(self.project_id)
        self.assertIsInstance(summary["runtime_available"], bool)
        text = repr(summary)
        self.assertNotIn(str(self.store.root.resolve()), text)
        self.assertNotIn("explicit-melt-command", text)
        self.assertIn("src_video", text)
        self.assertIn("clip_video", text)


if __name__ == "__main__":
    unittest.main()
