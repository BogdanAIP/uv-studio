from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore
from uv_studio.projects.transactions import ProjectUnitOfWork


class LegacyProjectTransactionCompatibilityTests(unittest.TestCase):
    def test_first_v2_transaction_undo_redo_preserves_exact_v1_project_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(
                title="Legacy transaction",
                recipe_id="general_video",
                project_id="prj_legacy_transaction",
            )
            project_path = store.project_path(project.project_id)

            legacy_payload = json.loads(project_path.read_text(encoding="utf-8"))
            compatibility = legacy_payload.pop("compatibility")
            legacy_payload["schema_version"] = 1
            legacy_payload["recipe_id"] = compatibility["recipe_id"]
            legacy_bytes = (
                json.dumps(
                    legacy_payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8")
            project_path.write_bytes(legacy_bytes)

            loaded = store.load_project(project.project_id)
            updated = replace(loaded, title="Migrated transaction")
            uow = ProjectUnitOfWork(store)
            committed = uow.commit(
                project.project_id,
                command="project.rename",
                documents={PROJECT_FILENAME: updated.to_dict()},
            )

            v2_bytes = project_path.read_bytes()
            self.assertNotEqual(v2_bytes, legacy_bytes)
            self.assertEqual(json.loads(v2_bytes)["schema_version"], 2)
            self.assertEqual(committed.history.cursor, 1)

            undone = uow.undo(project.project_id)
            self.assertEqual(undone.history.cursor, 0)
            self.assertEqual(project_path.read_bytes(), legacy_bytes)
            self.assertEqual(store.load_project(project.project_id).title, "Legacy transaction")

            redone = uow.redo(project.project_id)
            self.assertEqual(redone.history.cursor, 1)
            self.assertEqual(project_path.read_bytes(), v2_bytes)
            self.assertEqual(store.load_project(project.project_id).title, "Migrated transaction")


if __name__ == "__main__":
    unittest.main()
