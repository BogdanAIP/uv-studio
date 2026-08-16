from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.music_assembly import (
    MusicAssemblyError,
    MusicAssemblyStore,
    MusicVisualAssignment,
)
from uv_studio.projects.music_direction import MusicDirectionStore, MusicShotPlan
from uv_studio.projects.music_map import MusicExcerpt, MusicMapStore, MusicSection, MusicTimingMarker
from uv_studio.projects.store import ProjectStore


class MusicAssemblyTests(unittest.TestCase):
    def _add_source(
        self,
        store: ProjectStore,
        project_id: str,
        *,
        source_id: str,
        kind: str,
        payload: bytes,
        duration_us: int,
        suffix: str,
    ) -> ProjectReference:
        relative = f"sources/{source_id}{suffix}"
        path = store.project_directory(project_id) / relative
        path.write_bytes(payload)
        reference = ProjectReference(
            id=source_id,
            kind=kind,
            path=relative,
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": duration_us,
            },
        )
        project = store.load_project(project_id)
        store.update_project(project_id, sources=(*project.sources, reference))
        return reference

    def _setup(self, tmp: str):
        store = ProjectStore(Path(tmp) / "projects")
        project = store.create_project(title="Music assembly", recipe_id="music_video")
        project_id = project.project_id
        self._add_source(
            store,
            project_id,
            source_id="song",
            kind="audio",
            payload=b"assembly-song",
            duration_us=10_000_000,
            suffix=".wav",
        )
        self._add_source(
            store,
            project_id,
            source_id="clip_a",
            kind="video",
            payload=b"assembly-video-a",
            duration_us=12_000_000,
            suffix=".mp4",
        )
        self._add_source(
            store,
            project_id,
            source_id="clip_b",
            kind="video",
            payload=b"assembly-video-b",
            duration_us=8_000_000,
            suffix=".mp4",
        )
        music_map = MusicMapStore(store).set_map(
            project_id,
            song_reference_id="song",
            excerpt=MusicExcerpt(start_us=0, end_us=10_000_000),
            sections=(MusicSection("whole", "other", "Whole", 0, 10_000_000),),
            markers=(MusicTimingMarker("cut", "cut_point", 5_000_000),),
        )
        direction = MusicDirectionStore(store).set_direction(
            project_id,
            music_map_revision_sha256=music_map.revision_sha256,
            shots=(
                MusicShotPlan("shot_a", 0, 0, 5_000_000, "First visual", ("cut",)),
                MusicShotPlan("shot_b", 1, 5_000_000, 10_000_000, "Second visual"),
            ),
        )
        return store, project_id, direction

    def test_assembly_binds_every_shot_to_exact_verified_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, direction = self._setup(tmp)
            service = MusicAssemblyStore(store)
            self.assertIsNone(service.load(project_id))
            state = service.set_assembly(
                project_id,
                music_direction_revision_sha256=direction.revision_sha256,
                assignments=(
                    MusicVisualAssignment("shot_b", "clip_b", 0),
                    MusicVisualAssignment("shot_a", "clip_a", 1_000_000),
                ),
            )
            self.assertEqual([item.shot_id for item in state.bindings], ["shot_a", "shot_b"])
            self.assertEqual(state.bindings[0].source_start_us, 1_000_000)
            self.assertEqual(state.bindings[0].source_end_us, 6_000_000)
            reopened = service.load(project_id, validate_current=True)
            self.assertIsNotNone(reopened)
            assert reopened is not None
            self.assertEqual(reopened.revision_sha256, state.revision_sha256)

    def test_assembly_rejects_missing_duplicate_and_too_short_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, direction = self._setup(tmp)
            service = MusicAssemblyStore(store)
            with self.assertRaisesRegex(MusicAssemblyError, "exactly every"):
                service.set_assembly(
                    project_id,
                    music_direction_revision_sha256=direction.revision_sha256,
                    assignments=(MusicVisualAssignment("shot_a", "clip_a", 0),),
                )
            with self.assertRaisesRegex(MusicAssemblyError, "more than once"):
                service.set_assembly(
                    project_id,
                    music_direction_revision_sha256=direction.revision_sha256,
                    assignments=(
                        MusicVisualAssignment("shot_a", "clip_a", 0),
                        MusicVisualAssignment("shot_a", "clip_b", 0),
                    ),
                )
            with self.assertRaisesRegex(MusicAssemblyError, "too short"):
                service.set_assembly(
                    project_id,
                    music_direction_revision_sha256=direction.revision_sha256,
                    assignments=(
                        MusicVisualAssignment("shot_a", "clip_a", 8_000_000),
                        MusicVisualAssignment("shot_b", "clip_b", 0),
                    ),
                )

    def test_direction_revision_change_makes_assembly_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, direction = self._setup(tmp)
            service = MusicAssemblyStore(store)
            service.set_assembly(
                project_id,
                music_direction_revision_sha256=direction.revision_sha256,
                assignments=(
                    MusicVisualAssignment("shot_a", "clip_a", 0),
                    MusicVisualAssignment("shot_b", "clip_b", 0),
                ),
            )
            revised = MusicDirectionStore(store).set_direction(
                project_id,
                music_map_revision_sha256=direction.music_map_revision_sha256,
                shots=(
                    MusicShotPlan("shot_a", 0, 0, 5_000_000, "First visual revised", ("cut",)),
                    MusicShotPlan("shot_b", 1, 5_000_000, 10_000_000, "Second visual"),
                ),
            )
            self.assertNotEqual(revised.revision_sha256, direction.revision_sha256)
            with self.assertRaisesRegex(MusicAssemblyError, "stale"):
                service.load(project_id, validate_current=True)

    def test_source_byte_substitution_is_rejected_before_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id, direction = self._setup(tmp)
            service = MusicAssemblyStore(store)
            state = service.set_assembly(
                project_id,
                music_direction_revision_sha256=direction.revision_sha256,
                assignments=(
                    MusicVisualAssignment("shot_a", "clip_a", 0),
                    MusicVisualAssignment("shot_b", "clip_b", 0),
                ),
            )
            path = store.project_directory(project_id) / state.bindings[0].source_path
            path.write_bytes(b"substituted-video-bytes")
            with self.assertRaises(MusicAssemblyError):
                service.load(project_id, validate_current=True)


if __name__ == "__main__":
    unittest.main()
