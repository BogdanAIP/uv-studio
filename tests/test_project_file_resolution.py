from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectValidationError
from uv_studio.projects.store import ProjectStore


class ProjectFileResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Paths")
        self.project_dir = self.store.project_directory(self.project.project_id)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_windows_backslashes_are_normalized_to_project_path(self) -> None:
        target = self.project_dir / "sources" / "clip.mp4"
        target.write_bytes(b"x")
        resolved = self.store.resolve_project_file(
            self.project.project_id,
            "sources\\clip.mp4",
            must_exist=True,
            allowed_roots=("sources",),
        )
        self.assertEqual(resolved, target.resolve())

    def test_parent_traversal_is_rejected(self) -> None:
        with self.assertRaises(ProjectValidationError):
            self.store.resolve_project_file(
                self.project.project_id,
                "sources/../../outside.mp4",
                allowed_roots=("sources",),
            )

    def test_operation_cannot_write_to_unapproved_project_root(self) -> None:
        with self.assertRaises(ProjectValidationError):
            self.store.resolve_project_file(
                self.project.project_id,
                "sources/output.mp4",
                allowed_roots=("artifacts", "exports"),
            )

    def test_missing_nested_parent_is_rejected_instead_of_created(self) -> None:
        with self.assertRaises(ProjectValidationError):
            self.store.resolve_project_file(
                self.project.project_id,
                "artifacts/new/subdir/output.mp4",
                allowed_roots=("artifacts",),
            )
        self.assertFalse((self.project_dir / "artifacts" / "new").exists())

    def test_symlink_parent_cannot_escape_project(self) -> None:
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "secret.mp4").write_bytes(b"secret")
        link = self.project_dir / "sources" / "escape"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable on this runner: {exc}")
        with self.assertRaises(ProjectValidationError):
            self.store.resolve_project_file(
                self.project.project_id,
                "sources/escape/secret.mp4",
                must_exist=True,
                allowed_roots=("sources",),
            )


if __name__ == "__main__":
    unittest.main()
