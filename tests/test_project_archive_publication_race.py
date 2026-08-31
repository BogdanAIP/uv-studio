from __future__ import annotations

import json
import tempfile
import threading
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest import mock

import uv_studio.projects.archive as project_archive
from uv_studio.projects.archive import ARCHIVE_MANIFEST, ProjectArchiveError, export_project, import_project
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class ProjectArchivePublicationRaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source_store = ProjectStore(self.base / "source-projects")
        self.target_store = ProjectStore(self.base / "target-projects")
        self.project = self.source_store.create_project(
            title="Publication Fence Project",
            recipe_id="free_project",
            project_id="prj_publication_fence",
        )
        self.project_dir = self.source_store.project_directory(self.project.project_id)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_export_preserves_arbitrary_files_but_rejects_unpublished_uv_media_names(self) -> None:
        arbitrary = self.project_dir / "artifacts" / "preview" / "frame.txt"
        arbitrary.parent.mkdir(parents=True, exist_ok=True)
        arbitrary.write_text("portable-arbitrary-file", encoding="utf-8")

        managed = self.project_dir / "artifacts" / f"art_{uuid.uuid4().hex}.mp4"
        managed.write_bytes(b"unpublished-artifact")
        rejected = self.base / "rejected.uvproj.zip"
        with self.assertRaises(ProjectArchiveError) as caught:
            export_project(self.source_store, self.project.project_id, rejected)
        self.assertIn("unpublished managed media", str(caught.exception).lower())
        self.assertFalse(rejected.exists())

        managed.unlink()
        hidden_upload = self.project_dir / "assets" / (
            f".aud_{uuid.uuid4().hex}.wav.{uuid.uuid4().hex}.upload"
        )
        hidden_upload.write_bytes(b"partial-prepared-audio")
        with self.assertRaises(ProjectArchiveError) as caught:
            export_project(self.source_store, self.project.project_id, rejected)
        self.assertIn("unpublished managed media", str(caught.exception).lower())
        self.assertFalse(rejected.exists())

        hidden_upload.unlink()
        portable = self.base / "portable.uvproj.zip"
        export_project(self.source_store, self.project.project_id, portable)
        with zipfile.ZipFile(portable, "r") as archive:
            self.assertEqual(
                archive.read("project/artifacts/preview/frame.txt"),
                b"portable-arbitrary-file",
            )
            manifest = json.loads(archive.read(ARCHIVE_MANIFEST).decode("utf-8"))
            record = next(
                item
                for item in manifest["files"]
                if item["path"] == "project/artifacts/preview/frame.txt"
            )
            self.assertEqual(record["size"], len(b"portable-arbitrary-file"))

    def test_export_fails_closed_when_artifact_bytes_publish_before_reference(self) -> None:
        artifact_id = f"art_{uuid.uuid4().hex}"
        relative_path = f"artifacts/{artifact_id}.mp4"
        artifact_path = self.source_store.resolve_project_file(
            self.project.project_id,
            relative_path,
            allowed_roots=("artifacts",),
        )
        reference = ProjectReference(
            id=artifact_id,
            kind="video",
            path=relative_path,
            metadata={"lifecycle": "test_publication"},
        )
        archive_path = self.base / "concurrent.uvproj.zip"

        schema_sampled = threading.Event()
        release_export = threading.Event()
        bytes_published = threading.Event()
        metadata_started = threading.Event()
        metadata_completed = threading.Event()
        export_errors: list[BaseException] = []
        publisher_errors: list[BaseException] = []
        original_raw_schema = project_archive._raw_project_schema_version

        def sampled_schema(project_path: Path) -> int:
            version = original_raw_schema(project_path)
            schema_sampled.set()
            if not release_export.wait(timeout=5):
                raise RuntimeError("test did not release archive snapshot")
            return version

        def run_export() -> None:
            try:
                export_project(self.source_store, self.project.project_id, archive_path)
            except BaseException as exc:  # pragma: no cover - surfaced below
                export_errors.append(exc)

        def run_publisher() -> None:
            try:
                artifact_path.write_bytes(b"complete-artifact-bytes")
                bytes_published.set()
                metadata_started.set()
                self.source_store.update_project(
                    self.project.project_id,
                    artifacts=(*self.project.artifacts, reference),
                )
            except BaseException as exc:  # pragma: no cover - surfaced below
                publisher_errors.append(exc)
            finally:
                metadata_completed.set()

        export_thread = threading.Thread(target=run_export, daemon=True)
        publisher_thread = threading.Thread(target=run_publisher, daemon=True)
        with mock.patch(
            "uv_studio.projects.archive._raw_project_schema_version",
            side_effect=sampled_schema,
        ):
            export_thread.start()
            try:
                self.assertTrue(schema_sampled.wait(timeout=5))
                publisher_thread.start()
                self.assertTrue(bytes_published.wait(timeout=5))
                self.assertTrue(metadata_started.wait(timeout=5))
                self.assertFalse(
                    metadata_completed.wait(timeout=0.2),
                    "metadata publication must wait behind the archive snapshot fence",
                )
            finally:
                release_export.set()
                export_thread.join(timeout=5)
                publisher_thread.join(timeout=5)

        self.assertFalse(export_thread.is_alive())
        self.assertFalse(publisher_thread.is_alive())
        self.assertEqual(publisher_errors, [])
        self.assertEqual(len(export_errors), 1)
        self.assertIsInstance(export_errors[0], ProjectArchiveError)
        self.assertIn("unpublished managed media", str(export_errors[0]).lower())
        self.assertFalse(archive_path.exists())

        current = self.source_store.load_project(self.project.project_id)
        self.assertEqual([item.id for item in current.artifacts], [artifact_id])
        self.assertEqual(artifact_path.read_bytes(), b"complete-artifact-bytes")

        retry = self.base / "retry.uvproj.zip"
        export_project(self.source_store, self.project.project_id, retry)
        imported = import_project(self.target_store, retry)
        self.assertEqual([item.id for item in imported.artifacts], [artifact_id])
        imported_path = self.target_store.resolve_project_file(
            imported.project_id,
            relative_path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
        self.assertEqual(imported_path.read_bytes(), b"complete-artifact-bytes")


if __name__ == "__main__":
    unittest.main()
