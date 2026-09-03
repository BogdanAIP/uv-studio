from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from uv_studio.projects.archive import ProjectArchiveError, export_project
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.publication import (
    ManagedPublicationError,
    begin_managed_publication,
    pending_managed_publications,
    recover_managed_publications,
)
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore


class ManagedPublicationRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.store = ProjectStore(self.base / "projects")
        self.project = self.store.create_project(
            title="Publication recovery",
            recipe_id="general_video",
            project_id="prj_publication_recovery",
        )
        self.project_dir = self.store.project_directory(self.project.project_id)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _begin(self, relative_path: str, *, reference_id: str = "art_publication_recovery") -> str:
        with ProjectTaskRecordStore(self.store).project_lock(self.project.project_id):
            return begin_managed_publication(
                self.store,
                self.project.project_id,
                relative_path=relative_path,
                purpose="timeline.assemble",
                reference_id=reference_id,
            )

    def test_second_same_path_reservation_fails_while_old_marker_is_pending(self) -> None:
        relative_path = "artifacts/shared-user-selected-output.mp4"
        first_publication_id = self._begin(
            relative_path,
            reference_id="art_publication_first_owner",
        )
        output = self.store.resolve_project_file(
            self.project.project_id,
            relative_path,
            allowed_roots=("artifacts",),
        )
        self.assertFalse(output.exists())

        with self.assertRaisesRegex(ManagedPublicationError, "already reserved"):
            self._begin(
                relative_path,
                reference_id="art_publication_second_owner",
            )

        pending = pending_managed_publications(self.store, self.project.project_id)
        self.assertEqual(
            [(item["publication_id"], item["relative_path"]) for item in pending],
            [(first_publication_id, relative_path)],
        )
        self.assertFalse(output.exists())

        quarantined = recover_managed_publications(self.store, self.project.project_id)
        self.assertEqual(quarantined, ())
        self.assertEqual(pending_managed_publications(self.store, self.project.project_id), ())
        self.assertFalse(output.exists())

        second_publication_id = self._begin(
            relative_path,
            reference_id="art_publication_second_owner",
        )
        self.assertNotEqual(second_publication_id, first_publication_id)

    def test_case_alias_reservation_uses_filesystem_equivalent_identity(self) -> None:
        first_path = "artifacts/Clip.mp4"
        alias_path = "artifacts/clip.mp4"
        first_publication_id = self._begin(
            first_path,
            reference_id="art_publication_case_first",
        )

        with mock.patch(
            "uv_studio.projects.publication.os.path.normcase",
            side_effect=lambda value: str(value).lower(),
        ):
            with self.assertRaisesRegex(ManagedPublicationError, "already reserved"):
                self._begin(
                    alias_path,
                    reference_id="art_publication_case_second",
                )

        pending = pending_managed_publications(self.store, self.project.project_id)
        self.assertEqual(
            [(item["publication_id"], item["relative_path"]) for item in pending],
            [(first_publication_id, first_path)],
        )

    @unittest.skipUnless(os.name == "nt", "Windows case-insensitive filesystem regression")
    def test_windows_recovery_matches_registered_case_alias_without_quarantine(self) -> None:
        marker_path = "artifacts/Clip.mp4"
        registered_path = "artifacts/clip.mp4"
        artifact_id = "art_publication_windows_case_owner"
        self._begin(marker_path, reference_id=artifact_id)

        output = self.store.resolve_project_file(
            self.project.project_id,
            registered_path,
            allowed_roots=("artifacts",),
        )
        output.write_bytes(b"registered-windows-case-alias")
        project = self.store.load_project(self.project.project_id)
        artifact = ProjectReference(
            id=artifact_id,
            kind="video",
            path=registered_path,
            metadata={"capability_id": "timeline.assemble"},
        )
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, artifact),
        )

        quarantined = recover_managed_publications(self.store, self.project.project_id)
        self.assertEqual(quarantined, ())
        self.assertEqual(output.read_bytes(), b"registered-windows-case-alias")
        self.assertEqual(pending_managed_publications(self.store, self.project.project_id), ())
        durable = self.store.load_project(self.project.project_id)
        self.assertEqual(
            [(item.id, item.path) for item in durable.artifacts],
            [(artifact_id, registered_path)],
        )

    def test_archive_fails_closed_on_interrupted_arbitrary_path_publication(self) -> None:
        relative_path = "artifacts/custom-user-selected-output.mp4"
        publication_id = self._begin(relative_path)
        output = self.store.resolve_project_file(
            self.project.project_id,
            relative_path,
            allowed_roots=("artifacts",),
        )
        output.write_bytes(b"arbitrary-timeline-output")

        with self.assertRaisesRegex(ProjectArchiveError, "interrupted managed publication"):
            export_project(
                self.store,
                self.project.project_id,
                self.base / "interrupted.uvproj.zip",
            )

        pending = pending_managed_publications(self.store, self.project.project_id)
        self.assertEqual([item["publication_id"] for item in pending], [publication_id])

        quarantined = recover_managed_publications(self.store, self.project.project_id)
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].read_bytes(), b"arbitrary-timeline-output")
        self.assertFalse(output.exists())
        self.assertEqual(pending_managed_publications(self.store, self.project.project_id), ())

        archive = export_project(
            self.store,
            self.project.project_id,
            self.base / "recovered.uvproj.zip",
        )
        self.assertTrue(archive.is_file())

    def test_recovery_keeps_registered_output_and_only_clears_stale_marker(self) -> None:
        relative_path = "artifacts/custom-registered-output.mp4"
        artifact_id = "art_publication_registered"
        self._begin(relative_path, reference_id=artifact_id)
        output = self.store.resolve_project_file(
            self.project.project_id,
            relative_path,
            allowed_roots=("artifacts",),
        )
        output.write_bytes(b"registered-timeline-output")
        project = self.store.load_project(self.project.project_id)
        artifact = ProjectReference(
            id=artifact_id,
            kind="video",
            path=relative_path,
            metadata={"capability_id": "timeline.assemble"},
        )
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, artifact),
        )

        quarantined = recover_managed_publications(self.store, self.project.project_id)
        self.assertEqual(quarantined, ())
        self.assertEqual(output.read_bytes(), b"registered-timeline-output")
        self.assertEqual(pending_managed_publications(self.store, self.project.project_id), ())

        archive = export_project(
            self.store,
            self.project.project_id,
            self.base / "registered.uvproj.zip",
        )
        with zipfile.ZipFile(archive, "r") as zipped:
            self.assertIn(f"project/{relative_path}", zipped.namelist())

    def test_recovery_quarantines_bytes_when_same_path_has_different_reference(self) -> None:
        relative_path = "artifacts/reused-dangling-path.mp4"
        old_artifact = ProjectReference(
            id="art_publication_old_owner",
            kind="video",
            path=relative_path,
            metadata={"capability_id": "timeline.assemble", "fixture": "dangling"},
        )
        project = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            artifacts=(*project.artifacts, old_artifact),
        )

        publication_id = self._begin(
            relative_path,
            reference_id="art_publication_new_owner",
        )
        output = self.store.resolve_project_file(
            self.project.project_id,
            relative_path,
            allowed_roots=("artifacts",),
        )
        output.write_bytes(b"new-crash-left-bytes")

        quarantined = recover_managed_publications(self.store, self.project.project_id)
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].read_bytes(), b"new-crash-left-bytes")
        self.assertFalse(output.exists())
        self.assertEqual(pending_managed_publications(self.store, self.project.project_id), ())
        durable = self.store.load_project(self.project.project_id)
        self.assertEqual(
            [(item.id, item.path) for item in durable.artifacts],
            [(old_artifact.id, relative_path)],
        )
        self.assertIn(publication_id, quarantined[0].name)

    def test_ordinary_unregistered_artifact_remains_portable(self) -> None:
        ordinary = self.project_dir / "artifacts" / "preview" / "frame.txt"
        ordinary.parent.mkdir(parents=True, exist_ok=True)
        ordinary.write_text("portable-preview", encoding="utf-8")

        archive = export_project(
            self.store,
            self.project.project_id,
            self.base / "ordinary-portable.uvproj.zip",
        )
        with zipfile.ZipFile(archive, "r") as zipped:
            self.assertEqual(
                zipped.read("project/artifacts/preview/frame.txt").decode("utf-8"),
                "portable-preview",
            )

    def test_self_identifying_webvtt_and_generation_orphans_fail_closed(self) -> None:
        for name in (
            "sub_0123456789abcdef0123456789abcdef.vtt",
            "generated_attempt_0123456789abcdef0123456789abcdef.png",
        ):
            with self.subTest(name=name):
                path = self.project_dir / "artifacts" / name
                path.write_bytes(b"orphan")
                with self.assertRaisesRegex(ProjectArchiveError, "unpublished managed media"):
                    export_project(
                        self.store,
                        self.project.project_id,
                        self.base / f"{name}.uvproj.zip",
                    )
                path.unlink()


if __name__ == "__main__":
    unittest.main()
