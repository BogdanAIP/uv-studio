from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects import (
    EDIT_STATE_PATH,
    AcceptedRangeEdit,
    EditStateError,
    EditStateNotFound,
    ProjectStore,
    RangeEditState,
    RangeEditStateStore,
)


class RangeEditStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(title="Edit state")
        self.project_dir = self.store.project_directory(self.project.project_id)
        self.state_store = RangeEditStateStore(self.store)
        self.source = self.project_dir / "sources" / "source.mkv"
        self.replacement_a = self.project_dir / "artifacts" / "replacement-a.mkv"
        self.replacement_b = self.project_dir / "artifacts" / "replacement-b.mkv"
        self.source.write_bytes(b"source")
        self.replacement_a.write_bytes(b"replacement-a")
        self.replacement_b.write_bytes(b"replacement-b")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _edit(
        self,
        edit_id: str,
        start_us: int,
        end_us: int,
        replacement: str = "artifacts/replacement-a.mkv",
    ) -> AcceptedRangeEdit:
        return AcceptedRangeEdit(
            edit_id=edit_id,
            source_path="sources/source.mkv",
            start_us=start_us,
            end_us=end_us,
            replacement_path=replacement,
        )

    def test_accept_persists_only_typed_timeline_state(self) -> None:
        before_artifacts = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())
        state = self.state_store.accept(
            self.project.project_id,
            self._edit("edit_1", 1_000_000, 2_000_000),
        )
        after_artifacts = sorted(path.name for path in (self.project_dir / "artifacts").iterdir())

        self.assertEqual(before_artifacts, after_artifacts)
        self.assertEqual(len(state.edits), 1)
        state_path = self.project_dir / EDIT_STATE_PATH
        self.assertTrue(state_path.is_file())
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], 1)
        self.assertEqual(raw["edits"][0]["edit_id"], "edit_1")
        self.assertNotIn("provider", state_path.read_text(encoding="utf-8"))
        self.assertNotIn(str(self.project_dir), state_path.read_text(encoding="utf-8"))

    def test_non_overlapping_edits_are_sorted_deterministically(self) -> None:
        state = RangeEditState(
            edits=(
                self._edit("edit_b", 3_000_000, 4_000_000, "artifacts/replacement-b.mkv"),
                self._edit("edit_a", 1_000_000, 2_000_000),
            )
        )
        self.assertEqual([edit.edit_id for edit in state.edits], ["edit_a", "edit_b"])
        persisted = self.state_store.save(self.project.project_id, state)
        reloaded = self.state_store.load(self.project.project_id)
        self.assertEqual(reloaded, persisted)

    def test_touching_boundaries_are_allowed_but_overlap_is_rejected(self) -> None:
        state = RangeEditState(
            edits=(
                self._edit("edit_a", 1_000_000, 2_000_000),
                self._edit("edit_b", 2_000_000, 3_000_000, "artifacts/replacement-b.mkv"),
            )
        )
        self.assertEqual(len(state.edits), 2)
        with self.assertRaises(EditStateError):
            state.add(
                self._edit("edit_overlap", 1_500_000, 2_500_000, "artifacts/replacement-b.mkv")
            )

    def test_missing_source_or_replacement_fails_before_state_write(self) -> None:
        bad_source = AcceptedRangeEdit(
            edit_id="missing_source",
            source_path="sources/missing.mkv",
            start_us=0,
            end_us=1_000_000,
            replacement_path="artifacts/replacement-a.mkv",
        )
        with self.assertRaises(EditStateError):
            self.state_store.accept(self.project.project_id, bad_source)
        self.assertFalse((self.project_dir / EDIT_STATE_PATH).exists())

        bad_replacement = AcceptedRangeEdit(
            edit_id="missing_replacement",
            source_path="sources/source.mkv",
            start_us=0,
            end_us=1_000_000,
            replacement_path="artifacts/missing.mkv",
        )
        with self.assertRaises(EditStateError):
            self.state_store.accept(self.project.project_id, bad_replacement)
        self.assertFalse((self.project_dir / EDIT_STATE_PATH).exists())

    def test_remove_is_typed_and_missing_edit_is_explicit(self) -> None:
        self.state_store.accept(
            self.project.project_id,
            self._edit("edit_1", 1_000_000, 2_000_000),
        )
        state = self.state_store.remove(self.project.project_id, "edit_1")
        self.assertEqual(state.edits, ())
        with self.assertRaises(EditStateNotFound):
            self.state_store.remove(self.project.project_id, "edit_1")

    def test_absolute_and_parent_paths_are_rejected(self) -> None:
        with self.assertRaises(EditStateError):
            AcceptedRangeEdit(
                edit_id="bad_path",
                source_path="C:/video/source.mkv",
                start_us=0,
                end_us=1_000_000,
                replacement_path="artifacts/replacement-a.mkv",
            )
        with self.assertRaises(EditStateError):
            AcceptedRangeEdit(
                edit_id="bad_replacement",
                source_path="sources/source.mkv",
                start_us=0,
                end_us=1_000_000,
                replacement_path="../replacement.mkv",
            )


if __name__ == "__main__":
    unittest.main()
