from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest import mock

from uv_studio.projects.archive import ARCHIVE_MANIFEST, ProjectArchiveError, export_project, import_project
from uv_studio.projects.models import PROJECT_SCHEMA_VERSION, ProjectReference, compatibility_recipe_id, utc_now_iso
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.transactions import ProjectUnitOfWork


class _SimulatedHardCrash(BaseException):
    pass


class Stage19ArchivePreparedRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.store = ProjectStore(self.base / "source-projects")
        self.target_store = ProjectStore(self.base / "target-projects")
        self.project = self.store.create_project(
            title="Prepared recovery",
            recipe_id="general_video",
            project_id="prj_archive_prepared",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _leave_prepared_commit(self, *, command: str, project_payload: dict) -> None:
        original_atomic_write_json = self.store._atomic_write_json

        def crash_before_commit_marker(path: Path, data: dict) -> None:
            if path.parent.name == "transactions" and data.get("phase") == "committed":
                raise _SimulatedHardCrash("simulated process loss before transaction commit marker")
            original_atomic_write_json(path, data)

        with mock.patch.object(
            self.store,
            "_atomic_write_json",
            side_effect=crash_before_commit_marker,
        ):
            with self.assertRaises(_SimulatedHardCrash):
                ProjectUnitOfWork(self.store).commit(
                    self.project.project_id,
                    command=command,
                    documents={"project.json": project_payload},
                )

        transactions = sorted(
            (self.store.project_directory(self.project.project_id) / "history" / "transactions").glob(
                "*.json"
            )
        )
        self.assertEqual(len(transactions), 1)
        self.assertEqual(json.loads(transactions[0].read_text(encoding="utf-8"))["phase"], "prepared")

    def test_export_recovers_prepared_v1_to_v2_before_sampling_archive_state(self) -> None:
        project_path = self.store.project_path(self.project.project_id)
        raw = json.loads(project_path.read_text(encoding="utf-8"))
        compatibility = raw.pop("compatibility")
        raw["schema_version"] = 1
        raw["recipe_id"] = compatibility["recipe_id"]
        project_path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        legacy_bytes = project_path.read_bytes()
        migrated = self.store.load_project(self.project.project_id)
        self.assertEqual(migrated.schema_version, PROJECT_SCHEMA_VERSION)

        self._leave_prepared_commit(
            command="test.persist_schema_v2",
            project_payload=migrated.to_dict(),
        )
        self.assertEqual(json.loads(project_path.read_text(encoding="utf-8"))["schema_version"], 2)

        archive_path = export_project(
            self.store,
            self.project.project_id,
            self.base / "prepared-v1-v2.uvproj.zip",
        )

        self.assertEqual(project_path.read_bytes(), legacy_bytes)
        with zipfile.ZipFile(archive_path, "r") as archive:
            manifest = json.loads(archive.read(ARCHIVE_MANIFEST).decode("utf-8"))
            archived_project = archive.read("project/project.json")
        self.assertEqual(manifest["project_schema_version"], 1)
        self.assertEqual(archived_project, legacy_bytes)

        imported = import_project(self.target_store, archive_path)
        self.assertEqual(imported.schema_version, PROJECT_SCHEMA_VERSION)
        self.assertEqual(compatibility_recipe_id(imported), compatibility["recipe_id"])
        self.assertEqual(self.target_store.project_path(imported.project_id).read_bytes(), legacy_bytes)

    def test_export_uses_recovered_project_ownership_after_prepared_artifact_commit(self) -> None:
        artifact = ProjectReference(
            id="art_prepared_crash",
            kind="video",
            path=f"artifacts/art_{'a' * 32}.mp4",
            metadata={},
        )
        artifact_path = self.store.project_directory(self.project.project_id) / artifact.path
        artifact_path.write_bytes(b"prepared-artifact-bytes")
        after = replace(
            self.store.load_project(self.project.project_id),
            artifacts=(artifact,),
            updated_at=utc_now_iso(),
        )

        self._leave_prepared_commit(
            command="generation.register_output",
            project_payload=after.to_dict(),
        )
        self.assertEqual(
            [item.id for item in self.store.load_project(self.project.project_id).artifacts],
            [artifact.id],
        )

        with self.assertRaises(ProjectArchiveError) as caught:
            export_project(
                self.store,
                self.project.project_id,
                self.base / "prepared-artifact.uvproj.zip",
            )
        self.assertIn("unpublished managed media", str(caught.exception).lower())
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())
        self.assertEqual(artifact_path.read_bytes(), b"prepared-artifact-bytes")


if __name__ == "__main__":
    unittest.main()
