from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.projects.migrations import UnsupportedProjectSchema
from uv_studio.projects.models import ProjectReference, ProjectValidationError
from uv_studio.projects.store import (
    PROJECT_DIRECTORIES,
    ProjectAlreadyExists,
    ProjectNotFound,
    ProjectStore,
    ProjectStoreError,
)


class ProjectStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_project_writes_canonical_layout(self) -> None:
        project = self.store.create_project(
            title="First Project",
            recipe_id="general_video",
            project_id="prj_test",
        )
        self.assertEqual(project.project_id, "prj_test")
        path = self.root / "prj_test" / "project.json"
        self.assertTrue(path.is_file())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["recipe_id"], "general_video")
        for name in PROJECT_DIRECTORIES:
            self.assertTrue((self.root / "prj_test" / name).is_dir())

    def test_restart_can_load_existing_project(self) -> None:
        created = self.store.create_project(title="Persistent", project_id="prj_restart")
        restarted = ProjectStore(self.root)
        loaded = restarted.load_project("prj_restart")
        self.assertEqual(loaded.to_dict(), created.to_dict())

    def test_update_preserves_created_at_and_changes_data(self) -> None:
        created = self.store.create_project(title="Before", project_id="prj_update")
        source = ProjectReference(
            id="src_1",
            kind="source",
            path="sources/input.mp4",
            metadata={"role": "primary"},
        )
        updated = self.store.update_project(
            "prj_update",
            title="After",
            settings={"aspect_ratio": "16:9"},
            sources=[source],
        )
        self.assertEqual(updated.created_at, created.created_at)
        self.assertEqual(updated.title, "After")
        self.assertEqual(updated.settings["aspect_ratio"], "16:9")
        self.assertEqual(updated.sources[0].path, "sources/input.mp4")
        loaded = ProjectStore(self.root).load_project("prj_update")
        self.assertEqual(loaded.title, "After")

    def test_duplicate_project_is_rejected(self) -> None:
        self.store.create_project(title="One", project_id="prj_duplicate")
        with self.assertRaises(ProjectAlreadyExists):
            self.store.create_project(title="Two", project_id="prj_duplicate")

    def test_missing_project_is_explicit(self) -> None:
        with self.assertRaises(ProjectNotFound):
            self.store.load_project("prj_missing")

    def test_project_id_traversal_is_rejected(self) -> None:
        with self.assertRaises(ProjectValidationError):
            self.store.create_project(title="Bad", project_id="../escape")
        with self.assertRaises(ProjectValidationError):
            self.store.load_project("..\\escape")

    def test_reference_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(ProjectValidationError):
            ProjectReference(id="src_bad", kind="source", path="../outside.mp4")
        with self.assertRaises(ProjectValidationError):
            ProjectReference(id="src_bad2", kind="source", path="C:\\outside.mp4")

    def test_resolve_project_file_rechecks_allowed_root_after_symlink_resolution(self) -> None:
        project = self.store.create_project(title="Symlink boundary", project_id="prj_symlink")
        project_dir = self.store.project_directory(project.project_id)
        private = project_dir / "tasks" / "private.json"
        private.write_text('{"secret": true}\n', encoding="utf-8")
        alias = project_dir / "sources" / "alias.json"
        try:
            alias.symlink_to(Path("..") / "tasks" / "private.json")
        except OSError as exc:
            self.skipTest(f"symlinks are unavailable on this runner: {exc}")

        with self.assertRaises(ProjectValidationError):
            self.store.resolve_project_file(
                project.project_id,
                "sources/alias.json",
                must_exist=True,
                allowed_roots=("sources",),
            )

    def test_malformed_json_is_rejected(self) -> None:
        self.store.create_project(title="Broken", project_id="prj_broken")
        path = self.store.project_path("prj_broken")
        path.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(ProjectStoreError):
            self.store.load_project("prj_broken")

    def test_newer_schema_is_rejected(self) -> None:
        self.store.create_project(title="Future", project_id="prj_future")
        path = self.store.project_path("prj_future")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["schema_version"] = 999
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ProjectStoreError) as caught:
            self.store.load_project("prj_future")
        self.assertIn("newer than supported", str(caught.exception))

    def test_directory_id_must_match_document_id(self) -> None:
        self.store.create_project(title="Mismatch", project_id="prj_match")
        path = self.store.project_path("prj_match")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["project_id"] = "prj_other"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ProjectStoreError):
            self.store.load_project("prj_match")

    def test_failed_atomic_replace_leaves_previous_document_intact(self) -> None:
        self.store.create_project(title="Stable", project_id="prj_atomic")
        path = self.store.project_path("prj_atomic")
        before = path.read_bytes()

        with mock.patch.object(os, "replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                self.store.update_project("prj_atomic", title="Should Not Persist")

        self.assertEqual(path.read_bytes(), before)
        temporary_files = list(path.parent.glob(".project.json.*.tmp"))
        self.assertEqual(temporary_files, [])

    def test_list_projects_ignores_unrelated_directories(self) -> None:
        self.store.create_project(title="Older", project_id="prj_a")
        self.store.create_project(title="Newer", project_id="prj_b")
        (self.root / "not-a-project").mkdir()
        projects = self.store.list_projects()
        self.assertEqual({item.project_id for item in projects}, {"prj_a", "prj_b"})


if __name__ == "__main__":
    unittest.main()
