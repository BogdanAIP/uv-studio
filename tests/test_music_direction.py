from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.music_direction import (
    MusicDirectionError,
    MusicDirectionStore,
    MusicShotPlan,
)
from uv_studio.projects.music_map import (
    MusicExcerpt,
    MusicMapStore,
    MusicSection,
    MusicTimingMarker,
)
from uv_studio.projects.store import ProjectStore


class MusicDirectionTests(unittest.TestCase):
    def _setup_music(self, tmp: str):
        store = ProjectStore(Path(tmp) / "projects")
        project = store.create_project(title="Music direction", recipe_id="music_video")
        project_dir = store.project_directory(project.project_id)
        payload = b"direction-audio"
        path = project_dir / "sources" / "song.wav"
        path.write_bytes(payload)
        reference = ProjectReference(
            id="song",
            kind="audio",
            path="sources/song.wav",
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": 30_000_000,
            },
        )
        current = store.load_project(project.project_id)
        store.update_project(project.project_id, sources=(*current.sources, reference))
        music_map = MusicMapStore(store).set_map(
            project.project_id,
            song_reference_id="song",
            excerpt=MusicExcerpt(start_us=2_000_000, end_us=27_000_000),
            sections=(
                MusicSection("verse", "verse", "Verse", 2_000_000, 12_000_000),
                MusicSection("chorus", "chorus", "Chorus", 12_000_000, 27_000_000),
            ),
            markers=(
                MusicTimingMarker("beat_a", "downbeat", 7_000_000),
                MusicTimingMarker("beat_b", "beat", 12_000_000),
                MusicTimingMarker("peak", "climax", 20_000_000),
            ),
        )
        return store, project.project_id, music_map

    @staticmethod
    def _shots() -> tuple[MusicShotPlan, ...]:
        return (
            MusicShotPlan(
                "shot_1",
                0,
                2_000_000,
                7_000_000,
                "Establish performer.",
                ("beat_a",),
            ),
            MusicShotPlan(
                "shot_2",
                1,
                7_000_000,
                12_000_000,
                "Move into chorus.",
                ("beat_b",),
            ),
            MusicShotPlan(
                "shot_3",
                2,
                12_000_000,
                27_000_000,
                "Build through climax.",
                ("peak",),
                "fade",
            ),
        )

    def test_direction_binds_exact_map_and_covers_excerpt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, music_map = self._setup_music(tmp)
            service = MusicDirectionStore(store)
            self.assertIsNone(service.load(project_id))
            state = service.set_direction(
                project_id,
                music_map_revision_sha256=music_map.revision_sha256,
                shots=self._shots(),
            )
            reopened = service.load(project_id, validate_current=True)
            self.assertIsNotNone(reopened)
            assert reopened is not None
            self.assertEqual(reopened.revision_sha256, state.revision_sha256)
            self.assertEqual(reopened.shots[0].start_us, music_map.excerpt.start_us)
            self.assertEqual(reopened.shots[-1].end_us, music_map.excerpt.end_us)

    def test_direction_rejects_gap_unknown_marker_and_stale_map_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, music_map = self._setup_music(tmp)
            service = MusicDirectionStore(store)
            with self.assertRaisesRegex(MusicDirectionError, "contiguous timeline"):
                service.set_direction(
                    project_id,
                    music_map_revision_sha256=music_map.revision_sha256,
                    shots=(
                        MusicShotPlan("a", 0, 2_000_000, 7_000_000, "A"),
                        MusicShotPlan("b", 1, 8_000_000, 27_000_000, "B"),
                    ),
                )
            with self.assertRaisesRegex(MusicDirectionError, "unknown sync marker"):
                service.set_direction(
                    project_id,
                    music_map_revision_sha256=music_map.revision_sha256,
                    shots=(
                        MusicShotPlan("a", 0, 2_000_000, 27_000_000, "A", ("missing",)),
                    ),
                )
            with self.assertRaisesRegex(MusicDirectionError, "stale Music Map"):
                service.set_direction(
                    project_id,
                    music_map_revision_sha256="0" * 64,
                    shots=self._shots(),
                )

    def test_map_revision_change_makes_existing_direction_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, music_map = self._setup_music(tmp)
            service = MusicDirectionStore(store)
            service.set_direction(
                project_id,
                music_map_revision_sha256=music_map.revision_sha256,
                shots=self._shots(),
            )
            changed = MusicMapStore(store).set_map(
                project_id,
                song_reference_id="song",
                excerpt=MusicExcerpt(start_us=2_000_000, end_us=27_000_000),
                sections=(
                    MusicSection("verse", "verse", "Verse revised", 2_000_000, 12_000_000),
                    MusicSection("chorus", "chorus", "Chorus", 12_000_000, 27_000_000),
                ),
                markers=(
                    MusicTimingMarker("beat_a", "downbeat", 7_000_000),
                    MusicTimingMarker("beat_b", "beat", 12_000_000),
                    MusicTimingMarker("peak", "climax", 20_000_000),
                ),
            )
            self.assertNotEqual(changed.revision_sha256, music_map.revision_sha256)
            with self.assertRaisesRegex(MusicDirectionError, "stale"):
                service.load(project_id, validate_current=True)

    def test_rhythm_audit_prefers_explicit_sync_and_reports_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, music_map = self._setup_music(tmp)
            service = MusicDirectionStore(store)
            service.set_direction(
                project_id,
                music_map_revision_sha256=music_map.revision_sha256,
                shots=(
                    MusicShotPlan(
                        "shot_1",
                        0,
                        2_000_000,
                        7_080_000,
                        "Near downbeat.",
                        ("beat_a",),
                    ),
                    MusicShotPlan(
                        "shot_2",
                        1,
                        7_080_000,
                        12_350_000,
                        "Deliberately late cut.",
                        ("beat_b",),
                    ),
                    MusicShotPlan("shot_3", 2, 12_350_000, 27_000_000, "Finish."),
                ),
            )
            audit = service.rhythm_audit(project_id, tolerance_us=120_000)
            self.assertEqual(audit["cuts"][0]["target"]["target_id"], "beat_a")
            self.assertEqual(audit["cuts"][0]["delta_us"], 80_000)
            self.assertTrue(audit["cuts"][0]["aligned"])
            self.assertEqual(audit["cuts"][1]["target"]["target_id"], "beat_b")
            self.assertEqual(audit["cuts"][1]["delta_us"], 350_000)
            self.assertFalse(audit["cuts"][1]["aligned"])
            self.assertEqual(audit["summary"]["aligned_count"], 1)
            self.assertEqual(audit["summary"]["unaligned_count"], 1)
            self.assertFalse(audit["summary"]["all_aligned"])
            self.assertEqual(audit["summary"]["max_abs_delta_us"], 350_000)


if __name__ == "__main__":
    unittest.main()
