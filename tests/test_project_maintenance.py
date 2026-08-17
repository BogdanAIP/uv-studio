from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from uv_studio.projects import maintenance
from uv_studio.projects.maintenance import (
    ProjectMaintenanceError,
    prepare_project_store_for_current_schema,
    verify_migration_recovery_snapshot,
)
from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore


class ProjectMaintenanceTests(unittest.TestCase):
    def _store(self, root: Path, *project_ids: str) -> ProjectStore:
        store = ProjectStore(root / "projects")
        for project_id in project_ids:
            store.create_project(
                project_id=project_id,
                title=f"Project {project_id}",
                recipe_id="general_video",
            )
        return store

    @staticmethod
    def _fake_migration(data: dict[str, object]) -> dict[str, object]:
        migrated = deepcopy(data)
        settings = dict(migrated.get("settings", {}))
        if not settings.get("maintenance_test_migrated"):
            settings["maintenance_test_migrated"] = True
            migrated["settings"] = settings
        return migrated

    def test_current_schema_does_not_create_unnecessary_recovery_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root, "prj_current")
            recovery = root / "recovery"
            result = prepare_project_store_for_current_schema(store, recovery)
            self.assertEqual(result.migrated_project_ids, ())
            self.assertIsNone(result.recovery_snapshot)
            self.assertFalse(recovery.exists())

    def test_migration_snapshot_preserves_exact_original_metadata_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root, "prj_a")
            original = store.project_path("prj_a").read_bytes()
            recovery = root / "recovery"
            with patch(
                "uv_studio.projects.maintenance.migrate_project_data",
                side_effect=self._fake_migration,
            ):
                result = prepare_project_store_for_current_schema(store, recovery)
            self.assertEqual(result.migrated_project_ids, ("prj_a",))
            self.assertIsNotNone(result.recovery_snapshot)
            manifest = verify_migration_recovery_snapshot(result.recovery_snapshot)
            self.assertEqual(len(manifest["projects"]), 1)
            record = manifest["projects"][0]
            snapshot_file = result.recovery_snapshot.joinpath(*Path(record["path"]).parts)
            self.assertEqual(snapshot_file.read_bytes(), original)
            migrated = json.loads(store.project_path("prj_a").read_text(encoding="utf-8"))
            self.assertTrue(migrated["settings"]["maintenance_test_migrated"])

    def test_snapshot_detects_same_size_metadata_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root, "prj_a")
            with patch(
                "uv_studio.projects.maintenance.migrate_project_data",
                side_effect=self._fake_migration,
            ):
                result = prepare_project_store_for_current_schema(store, root / "recovery")
            manifest = verify_migration_recovery_snapshot(result.recovery_snapshot)
            record = manifest["projects"][0]
            snapshot_file = result.recovery_snapshot.joinpath(*Path(record["path"]).parts)
            payload = bytearray(snapshot_file.read_bytes())
            self.assertTrue(payload)
            payload[len(payload) // 2] ^= 1
            snapshot_file.write_bytes(payload)
            with self.assertRaisesRegex(ProjectMaintenanceError, "SHA-256 mismatch"):
                verify_migration_recovery_snapshot(result.recovery_snapshot)

    def test_all_projects_preflight_before_any_snapshot_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root, "prj_a", "prj_b")
            original_a = store.project_path("prj_a").read_bytes()
            original_b = store.project_path("prj_b").read_bytes()

            def migrate(data: dict[str, object]) -> dict[str, object]:
                if data.get("project_id") == "prj_b":
                    raise ValueError("synthetic preflight failure")
                return self._fake_migration(data)

            recovery = root / "recovery"
            with patch("uv_studio.projects.maintenance.migrate_project_data", side_effect=migrate):
                with self.assertRaisesRegex(ProjectMaintenanceError, "cannot be prepared"):
                    prepare_project_store_for_current_schema(store, recovery)
            self.assertEqual(store.project_path("prj_a").read_bytes(), original_a)
            self.assertEqual(store.project_path("prj_b").read_bytes(), original_b)
            self.assertFalse(recovery.exists())

    def test_partial_migration_write_rolls_back_exact_bytes_and_keeps_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root, "prj_a", "prj_b")
            originals = {
                project_id: store.project_path(project_id).read_bytes()
                for project_id in ("prj_a", "prj_b")
            }
            real_write = maintenance._atomic_write_bytes
            project_write_count = 0

            def flaky_write(path: Path, payload: bytes) -> None:
                nonlocal project_write_count
                if path.name == PROJECT_FILENAME and path.parent.parent == store.root:
                    project_write_count += 1
                    if project_write_count == 2:
                        raise OSError("synthetic second-project write failure")
                real_write(path, payload)

            recovery = root / "recovery"
            with (
                patch(
                    "uv_studio.projects.maintenance.migrate_project_data",
                    side_effect=self._fake_migration,
                ),
                patch("uv_studio.projects.maintenance._atomic_write_bytes", side_effect=flaky_write),
            ):
                with self.assertRaisesRegex(ProjectMaintenanceError, "original metadata was restored"):
                    prepare_project_store_for_current_schema(store, recovery)

            for project_id, original in originals.items():
                self.assertEqual(store.project_path(project_id).read_bytes(), original)
            published_sets = [entry for entry in recovery.iterdir() if entry.is_dir()]
            self.assertEqual(len(published_sets), 1)
            verify_migration_recovery_snapshot(published_sets[0])
            self.assertFalse(any(entry.name.endswith(".staging") for entry in recovery.iterdir()))

    def test_newer_project_schema_fails_before_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root, "prj_future")
            project_path = store.project_path("prj_future")
            data = json.loads(project_path.read_text(encoding="utf-8"))
            data["schema_version"] = 999
            project_path.write_text(json.dumps(data), encoding="utf-8")
            recovery = root / "recovery"
            with self.assertRaisesRegex(ProjectMaintenanceError, "cannot be prepared"):
                prepare_project_store_for_current_schema(store, recovery)
            self.assertFalse(recovery.exists())


if __name__ == "__main__":
    unittest.main()
