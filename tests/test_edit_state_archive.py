from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    AcceptedRangeEdit,
    EditStateError,
    ProjectStore,
    RangeEditStateStore,
    export_project,
    import_project,
)


class EditStateArchiveTests(unittest.TestCase):
    def test_export_import_and_fresh_store_reopen_preserve_edit_decisions_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_store = ProjectStore(root / "source-projects")
            project = source_store.create_project(title="Portable edits", project_id="prj_edits")
            project_dir = source_store.project_directory(project.project_id)
            (project_dir / "sources" / "source.mkv").write_bytes(b"source-media")
            (project_dir / "artifacts" / "replace-a.mkv").write_bytes(b"replacement-a")
            (project_dir / "artifacts" / "replace-b.mkv").write_bytes(b"replacement-b")

            expected = RangeEditStateStore(source_store).accept(
                project.project_id,
                AcceptedRangeEdit(
                    edit_id="edit_a",
                    source_path="sources/source.mkv",
                    start_us=1_000_000,
                    end_us=2_000_000,
                    replacement_path="artifacts/replace-a.mkv",
                ),
            )
            expected = RangeEditStateStore(source_store).accept(
                project.project_id,
                AcceptedRangeEdit(
                    edit_id="edit_b",
                    source_path="sources/source.mkv",
                    start_us=3_000_000,
                    end_us=4_000_000,
                    replacement_path="artifacts/replace-b.mkv",
                ),
            )

            archive = export_project(source_store, project.project_id, root / "portable.uvproj.zip")
            target_root = root / "target-projects"
            imported = import_project(ProjectStore(target_root), archive)
            self.assertEqual(imported.project_id, project.project_id)

            fresh_store = ProjectStore(target_root)
            reopened = RangeEditStateStore(fresh_store).load(project.project_id)
            self.assertEqual(reopened, expected)
            self.assertEqual(
                [edit.to_dict() for edit in reopened.edits],
                [edit.to_dict() for edit in expected.edits],
            )

    def test_corrupt_reopened_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(title="Corrupt edit state")
            project_dir = store.project_directory(project.project_id)
            state_path = project_dir / "timeline" / "range-edits.json"
            state_path.write_text(
                '{"schema_version":1,"edits":[{"edit_id":"bad","source_path":"../escape.mkv","start_us":0,"end_us":1000000,"replacement_path":"artifacts/x.mkv"}]}',
                encoding="utf-8",
            )
            with self.assertRaises(EditStateError):
                RangeEditStateStore(store).load(project.project_id)


if __name__ == "__main__":
    unittest.main()
