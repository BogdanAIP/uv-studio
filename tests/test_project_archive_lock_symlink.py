from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.archive import ProjectArchiveError, _iter_project_entries, export_project
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordConflict, ProjectTaskRecordStore


class ProjectArchiveLockSymlinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.store = ProjectStore(self.base / "projects")
        self.project = self.store.create_project(
            title="Archive Lock Symlink",
            recipe_id="general_video",
            project_id="prj_archive_lock_symlink",
        )
        self.project_dir = self.store.project_path(self.project.project_id).parent

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _install_lock_symlink(self) -> tuple[Path, Path]:
        tasks_dir = self.project_dir / "tasks"
        target = tasks_dir / "lock-target.bin"
        target.write_bytes(b"")
        lock_path = tasks_dir / ProjectTaskRecordStore.LOCK_FILE_NAME
        try:
            lock_path.symlink_to(target.name, target_is_directory=False)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"filesystem symlinks unavailable: {exc}")
        self.assertTrue(lock_path.is_symlink())
        return lock_path, target

    def test_project_lock_rejects_symlink_without_mutating_target(self) -> None:
        _lock_path, target = self._install_lock_symlink()

        with self.assertRaises(ProjectTaskRecordConflict):
            with ProjectTaskRecordStore(self.store).project_lock(self.project.project_id):
                self.fail("symlink project lock must never be acquired")

        self.assertEqual(target.read_bytes(), b"")

    def test_export_rejects_transient_lock_symlink_before_lock_acquisition(self) -> None:
        lock_path, target = self._install_lock_symlink()
        archive = self.base / "should-not-exist.uvproj.zip"

        with self.assertRaises(ProjectArchiveError) as caught:
            export_project(self.store, self.project.project_id, archive)

        self.assertIn(str(lock_path), str(caught.exception))
        self.assertEqual(target.read_bytes(), b"")
        self.assertFalse(archive.exists())

    def test_archive_enumeration_does_not_bypass_transient_symlink(self) -> None:
        lock_path, target = self._install_lock_symlink()

        with self.assertRaises(ProjectArchiveError) as caught:
            _iter_project_entries(self.project_dir)

        self.assertIn(str(lock_path), str(caught.exception))
        self.assertEqual(target.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
