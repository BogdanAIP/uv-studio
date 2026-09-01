from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.generation.jobs import GenerationJobManager
from uv_studio.generation.recovery import recover_interrupted_project_jobs
from uv_studio.projects.archive import ProjectArchiveError, export_project
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class Stage19ArtOrphanRecoveryTests(unittest.TestCase):
    def test_startup_recovery_quarantines_unregistered_legacy_art_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = ProjectStore(base / "projects")
            project = store.create_project(
                title="Legacy art crash recovery",
                recipe_id="general_video",
                project_id="prj_stage19_art_orphan",
            )
            project_dir = store.project_directory(project.project_id)
            output = project_dir / "artifacts" / "art_0123456789abcdef0123456789abcdef.mp4"
            output.write_bytes(b"legacy-renderer-crash-left-bytes")

            with self.assertRaisesRegex(ProjectArchiveError, "unpublished managed media"):
                export_project(store, project.project_id, base / "before-recovery.uvproj.zip")

            manager = GenerationJobManager(store)
            self.assertEqual(recover_interrupted_project_jobs(manager, project.project_id), ())

            self.assertFalse(output.exists())
            quarantined = tuple(
                store.root.glob(
                    f".uv-recovered-orphan-{project.project_id}-*-{output.name}"
                )
            )
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0].read_bytes(), b"legacy-renderer-crash-left-bytes")

            archive = export_project(
                store,
                project.project_id,
                base / "after-recovery.uvproj.zip",
            )
            self.assertTrue(archive.is_file())

    def test_startup_recovery_preserves_registered_art_output_and_near_miss_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = ProjectStore(base / "projects")
            project = store.create_project(
                title="Legacy art recovery boundaries",
                recipe_id="general_video",
                project_id="prj_stage19_art_boundaries",
            )
            project_dir = store.project_directory(project.project_id)
            registered_path = "artifacts/art_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.mp4"
            registered = project_dir / registered_path
            registered.write_bytes(b"registered-art")
            near_miss = project_dir / "artifacts" / "art_preview.mp4"
            near_miss.write_bytes(b"ordinary-portable-file")

            current = store.load_project(project.project_id)
            store.update_project(
                project.project_id,
                artifacts=(
                    *current.artifacts,
                    ProjectReference(
                        id="art_stage19_registered",
                        kind="video",
                        path=registered_path,
                        metadata={"capability_id": "audio.visualize"},
                    ),
                ),
            )

            manager = GenerationJobManager(store)
            self.assertEqual(recover_interrupted_project_jobs(manager, project.project_id), ())

            self.assertEqual(registered.read_bytes(), b"registered-art")
            self.assertEqual(near_miss.read_bytes(), b"ordinary-portable-file")
            self.assertEqual(tuple(store.root.glob(".uv-recovered-orphan-*")), ())

    def test_startup_recovery_quarantines_prepared_audio_final_and_staging_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = ProjectStore(base / "projects")
            project = store.create_project(
                title="Prepared audio crash recovery",
                recipe_id="general_video",
                project_id="prj_stage19_audio_orphan",
            )
            project_dir = store.project_directory(project.project_id)
            assets = project_dir / "assets"
            outputs = {
                assets / "aud_0123456789abcdef0123456789abcdef.wav": b"final-audio-crash-left",
                assets
                / ".aud_11111111111111111111111111111111.wav.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.upload": b"upload-staging-crash-left",
                assets
                / ".aud_22222222222222222222222222222222.wav.bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.promote": b"promotion-staging-crash-left",
            }
            for path, payload in outputs.items():
                path.write_bytes(payload)

            with self.assertRaisesRegex(ProjectArchiveError, "unpublished managed media"):
                export_project(store, project.project_id, base / "before-audio-recovery.uvproj.zip")

            manager = GenerationJobManager(store)
            self.assertEqual(recover_interrupted_project_jobs(manager, project.project_id), ())

            for path, payload in outputs.items():
                self.assertFalse(path.exists())
                quarantined = tuple(
                    store.root.glob(
                        f".uv-recovered-orphan-{project.project_id}-*-{path.name}"
                    )
                )
                self.assertEqual(len(quarantined), 1)
                self.assertEqual(quarantined[0].read_bytes(), payload)

            archive = export_project(
                store,
                project.project_id,
                base / "after-audio-recovery.uvproj.zip",
            )
            self.assertTrue(archive.is_file())

    def test_startup_recovery_preserves_registered_prepared_audio_and_near_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = ProjectStore(base / "projects")
            project = store.create_project(
                title="Prepared audio recovery boundaries",
                recipe_id="general_video",
                project_id="prj_stage19_audio_boundaries",
            )
            project_dir = store.project_directory(project.project_id)
            registered_path = "assets/aud_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.wav"
            registered = project_dir / registered_path
            registered.write_bytes(b"registered-prepared-audio")
            near_miss = project_dir / "assets" / "aud_preview.wav"
            near_miss.write_bytes(b"ordinary-portable-audio")

            current = store.load_project(project.project_id)
            store.update_project(
                project.project_id,
                artifacts=(
                    *current.artifacts,
                    ProjectReference(
                        id="aud_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        kind="audio",
                        path=registered_path,
                        metadata={"role": "prepared-speech"},
                    ),
                ),
            )

            manager = GenerationJobManager(store)
            self.assertEqual(recover_interrupted_project_jobs(manager, project.project_id), ())

            self.assertEqual(registered.read_bytes(), b"registered-prepared-audio")
            self.assertEqual(near_miss.read_bytes(), b"ordinary-portable-audio")
            self.assertEqual(tuple(store.root.glob(".uv-recovered-orphan-*")), ())


if __name__ == "__main__":
    unittest.main()
