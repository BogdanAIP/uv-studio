from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.editor.commands import (
    EditorCommandError,
    EditorCommandService,
    RemoveAcceptedEditCommand,
)
from uv_studio.projects import AcceptedRangeEdit, EditStateNotFound, ProjectStore, RangeEditStateStore


class EditorCommandConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(recipe_id="general_video", title="Editor command conformance")
        project_dir = self.store.project_directory(self.project.project_id)
        (project_dir / "sources" / "source.mkv").write_bytes(b"source")
        (project_dir / "artifacts" / "replacement.mkv").write_bytes(b"replacement")
        RangeEditStateStore(self.store).accept(
            self.project.project_id,
            AcceptedRangeEdit(
                edit_id="edit_1",
                source_path="sources/source.mkv",
                start_us=1_000_000,
                end_us=2_000_000,
                replacement_path="artifacts/replacement.mkv",
            ),
        )
        self.service = EditorCommandService(self.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_remove_accepted_edit_mutates_canonical_state_through_command_service(self) -> None:
        result = self.service.remove_accepted_edit(
            self.project.project_id,
            RemoveAcceptedEditCommand(edit_id="edit_1"),
        )

        self.assertEqual(result.command, "remove_accepted_edit")
        self.assertEqual(result.edit_id, "edit_1")
        self.assertEqual(result.state.edits, ())
        self.assertEqual(RangeEditStateStore(self.store).load(self.project.project_id).edits, ())

    def test_remove_accepted_edit_preserves_not_found_semantics(self) -> None:
        with self.assertRaises(EditStateNotFound):
            self.service.remove_accepted_edit(
                self.project.project_id,
                RemoveAcceptedEditCommand(edit_id="edit_missing"),
            )

    def test_remove_accepted_edit_rejects_invalid_identifier_before_mutation(self) -> None:
        with self.assertRaises(EditorCommandError):
            RemoveAcceptedEditCommand(edit_id="../edit_1")

        state = RangeEditStateStore(self.store).load(self.project.project_id)
        self.assertEqual([edit.edit_id for edit in state.edits], ["edit_1"])


if __name__ == "__main__":
    unittest.main()
