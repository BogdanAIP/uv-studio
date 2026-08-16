from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.archive import export_project, import_project
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.music_direction import MusicDirectionStore, MusicShotPlan
from uv_studio.projects.music_map import (
    MusicExcerpt,
    MusicMapStore,
    MusicSection,
    MusicTimingMarker,
)
from uv_studio.projects.store import ProjectStore


class MusicWorkflowArchiveTests(unittest.TestCase):
    def test_export_import_preserves_music_map_direction_and_exact_song_binding(self) -> None:
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as target_tmp:
            source = ProjectStore(Path(source_tmp) / "projects")
            project = source.create_project(title="Portable music workflow", recipe_id="music_video")
            project_dir = source.project_directory(project.project_id)
            song_bytes = b"portable-music-song"
            (project_dir / "sources" / "song.wav").write_bytes(song_bytes)
            reference = ProjectReference(
                id="song",
                kind="audio",
                path="sources/song.wav",
                metadata={
                    "sha256": hashlib.sha256(song_bytes).hexdigest(),
                    "size_bytes": len(song_bytes),
                    "duration_us": 24_000_000,
                },
            )
            current = source.load_project(project.project_id)
            source.update_project(project.project_id, sources=(*current.sources, reference))

            music_map = MusicMapStore(source).set_map(
                project.project_id,
                song_reference_id="song",
                excerpt=MusicExcerpt(start_us=2_000_000, end_us=22_000_000),
                sections=(
                    MusicSection("verse", "verse", "Verse", 2_000_000, 12_000_000),
                    MusicSection("chorus", "chorus", "Chorus", 12_000_000, 22_000_000),
                ),
                markers=(
                    MusicTimingMarker("cut_a", "downbeat", 8_000_000),
                    MusicTimingMarker("cut_b", "beat", 12_000_000),
                ),
            )
            direction = MusicDirectionStore(source).set_direction(
                project.project_id,
                music_map_revision_sha256=music_map.revision_sha256,
                shots=(
                    MusicShotPlan("shot_1", 0, 2_000_000, 8_000_000, "Verse shot", ("cut_a",)),
                    MusicShotPlan("shot_2", 1, 8_000_000, 12_000_000, "Turn", ("cut_b",)),
                    MusicShotPlan("shot_3", 2, 12_000_000, 22_000_000, "Chorus shot"),
                ),
            )

            archive = Path(source_tmp) / "music.uvproj.zip"
            export_project(source, project.project_id, archive)

            target = ProjectStore(Path(target_tmp) / "projects")
            imported = import_project(target, archive)
            self.assertEqual(imported.project_id, project.project_id)

            reopened_map = MusicMapStore(target).load(project.project_id, validate_current=True)
            reopened_direction = MusicDirectionStore(target).load(
                project.project_id, validate_current=True
            )
            self.assertIsNotNone(reopened_map)
            self.assertIsNotNone(reopened_direction)
            assert reopened_map is not None and reopened_direction is not None
            self.assertEqual(reopened_map.revision_sha256, music_map.revision_sha256)
            self.assertEqual(reopened_direction.revision_sha256, direction.revision_sha256)
            self.assertEqual(reopened_map.song.sha256, hashlib.sha256(song_bytes).hexdigest())
            self.assertEqual(reopened_direction.music_map_revision_sha256, reopened_map.revision_sha256)


if __name__ == "__main__":
    unittest.main()
