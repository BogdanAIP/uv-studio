from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from uv_studio.projects.archive import export_project, import_project
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference, utc_now_iso
from uv_studio.projects.production_state import (
    ProductionDocumentNotFound,
    ProductionDocumentStore,
)
from uv_studio.projects.store import PROJECT_FILENAME, ProjectStore
from uv_studio.projects.timeline import (
    MAIN_TIMELINE_PATH,
    TimelineClip,
    TimelineDocument,
    TimelineStore,
    TimelineTrack,
)
from uv_studio.projects.transactions import (
    NothingToRedo,
    ProjectTransactionConflict,
    ProjectTransactionError,
    ProjectUnitOfWork,
)


class ProjectUnitOfWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Transactional Studio",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_transactions",
        )
        asset_path = self.store.resolve_project_file(
            self.project.project_id,
            "assets/take_1.mp4",
            allowed_roots=("assets",),
        )
        asset_path.write_bytes(b"accepted-take")
        self.asset = ProjectReference(
            id="asset_take_1",
            kind="video",
            path="assets/take_1.mp4",
            metadata={"duration_us": 4_000_000},
        )
        self.production_payload = {
            "schema_version": 1,
            "document_kind": "transaction-proof",
            "accepted_asset_id": self.asset.id,
        }
        self.timeline = TimelineDocument(
            tracks=(
                TimelineTrack(
                    track_id="trk_video",
                    kind="video",
                    title="Video 1",
                    clips=(
                        TimelineClip(
                            clip_id="clip_take_1",
                            reference_id=self.asset.id,
                            timeline_start_us=0,
                            source_start_us=0,
                            duration_us=4_000_000,
                        ),
                    ),
                ),
            ),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _documents(self, *, title: str = "Transactional Studio") -> dict[str, dict]:
        project = replace(
            self.store.load_project(self.project.project_id),
            title=title,
            artifacts=(self.asset,),
            updated_at=utc_now_iso(),
        )
        return {
            PROJECT_FILENAME: project.to_dict(),
            "production/shared.json": self.production_payload,
            MAIN_TIMELINE_PATH: self.timeline.to_dict(),
        }

    def test_one_transaction_spans_project_production_and_timeline_with_durable_undo_redo(self) -> None:
        uow = ProjectUnitOfWork(self.store)
        committed = uow.commit(
            self.project.project_id,
            command="production.accept_take",
            documents=self._documents(),
        )

        self.assertTrue(committed.transaction_id.startswith("tx_"))
        self.assertEqual(committed.history.cursor, 1)
        self.assertEqual(committed.history.entries[0].command, "production.accept_take")
        self.assertEqual(
            set(committed.history.entries[0].changed_paths),
            {PROJECT_FILENAME, "production/shared.json", MAIN_TIMELINE_PATH},
        )
        self.assertEqual(
            [item.id for item in self.store.load_project(self.project.project_id).artifacts],
            [self.asset.id],
        )
        self.assertEqual(
            ProductionDocumentStore(self.store).load(self.project.project_id, "shared"),
            self.production_payload,
        )
        self.assertEqual(
            TimelineStore(self.store).load(self.project.project_id).tracks[0].clips[0].reference_id,
            self.asset.id,
        )

        transaction_path = (
            self.store.project_directory(self.project.project_id)
            / "history"
            / "transactions"
            / f"{committed.transaction_id}.json"
        )
        self.assertEqual(json.loads(transaction_path.read_text(encoding="utf-8"))["phase"], "committed")

        restarted = ProjectUnitOfWork(ProjectStore(self.store.root))
        undone = restarted.undo(self.project.project_id)
        self.assertEqual(undone.transaction_id, committed.transaction_id)
        self.assertEqual(undone.history.cursor, 0)
        self.assertEqual(self.store.load_project(self.project.project_id).artifacts, ())
        with self.assertRaises(ProductionDocumentNotFound):
            ProductionDocumentStore(self.store).load(self.project.project_id, "shared")
        self.assertEqual(TimelineStore(self.store).load(self.project.project_id).tracks, ())

        redone = ProjectUnitOfWork(ProjectStore(self.store.root)).redo(self.project.project_id)
        self.assertEqual(redone.transaction_id, committed.transaction_id)
        self.assertEqual(redone.history.cursor, 1)
        self.assertEqual(
            [item.id for item in self.store.load_project(self.project.project_id).artifacts],
            [self.asset.id],
        )
        self.assertEqual(
            TimelineStore(self.store).load(self.project.project_id).tracks[0].clips[0].clip_id,
            "clip_take_1",
        )

    def test_failed_multidocument_commit_restores_exact_original_bytes(self) -> None:
        production = ProductionDocumentStore(self.store)
        production.save(
            self.project.project_id,
            "shared",
            {"schema_version": 1, "document_kind": "before"},
        )
        TimelineStore(self.store).save(self.project.project_id, TimelineDocument())

        watched_paths = [
            self.store.project_path(self.project.project_id),
            self.store.resolve_project_file(
                self.project.project_id,
                "production/shared.json",
                must_exist=True,
                allowed_roots=("production",),
            ),
            self.store.resolve_project_file(
                self.project.project_id,
                MAIN_TIMELINE_PATH,
                must_exist=True,
                allowed_roots=("timeline",),
            ),
        ]
        before = {path: path.read_bytes() for path in watched_paths}
        uow = ProjectUnitOfWork(self.store)
        original_write = uow._write_snapshot
        calls = 0

        def fail_once(project_id: str, snapshot: dict) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated second-document failure")
            original_write(project_id, snapshot)

        with mock.patch.object(uow, "_write_snapshot", side_effect=fail_once):
            with self.assertRaisesRegex(ProjectTransactionError, "rolled back"):
                uow.commit(
                    self.project.project_id,
                    command="production.accept_take",
                    documents=self._documents(title="Must Roll Back"),
                )

        self.assertEqual({path: path.read_bytes() for path in watched_paths}, before)
        history = ProjectUnitOfWork(self.store).history(self.project.project_id)
        self.assertEqual(history.entries, ())
        self.assertEqual(history.cursor, 0)

    def test_undo_rejects_out_of_band_canonical_change(self) -> None:
        uow = ProjectUnitOfWork(self.store)
        uow.commit(
            self.project.project_id,
            command="production.accept_take",
            documents=self._documents(),
        )
        production_path = self.store.resolve_project_file(
            self.project.project_id,
            "production/shared.json",
            must_exist=True,
            allowed_roots=("production",),
        )
        production_path.write_text(
            '{"schema_version": 1, "document_kind": "out-of-band"}\n',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ProjectTransactionConflict, "outside transaction history"):
            uow.undo(self.project.project_id)

        self.assertIn("out-of-band", production_path.read_text(encoding="utf-8"))
        self.assertEqual(uow.history(self.project.project_id).cursor, 1)

    def test_prepared_transaction_is_rolled_back_after_process_interruption(self) -> None:
        project_path = self.store.project_path(self.project.project_id)
        before_project = project_path.read_bytes()
        uow = ProjectUnitOfWork(self.store)

        with mock.patch.object(uow, "_write_history", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                uow.commit(
                    self.project.project_id,
                    command="production.interrupted",
                    documents=self._documents(title="Interrupted Write"),
                )

        self.assertEqual(self.store.load_project(self.project.project_id).title, "Interrupted Write")
        recovered = ProjectUnitOfWork(ProjectStore(self.store.root)).history(
            self.project.project_id
        )
        self.assertEqual(recovered.entries, ())
        self.assertEqual(recovered.cursor, 0)
        self.assertEqual(project_path.read_bytes(), before_project)
        with self.assertRaises(ProductionDocumentNotFound):
            ProductionDocumentStore(self.store).load(self.project.project_id, "shared")
        self.assertEqual(TimelineStore(self.store).load(self.project.project_id).tracks, ())

    def test_new_commit_after_undo_truncates_redo_branch(self) -> None:
        uow = ProjectUnitOfWork(self.store)
        first = uow.commit(
            self.project.project_id,
            command="project.first",
            documents=self._documents(title="First"),
        )
        second = uow.commit(
            self.project.project_id,
            command="project.second",
            documents={
                PROJECT_FILENAME: replace(
                    self.store.load_project(self.project.project_id),
                    title="Second",
                    updated_at=utc_now_iso(),
                ).to_dict()
            },
        )
        self.assertNotEqual(first.transaction_id, second.transaction_id)
        uow.undo(self.project.project_id)

        replacement = uow.commit(
            self.project.project_id,
            command="project.replacement",
            documents={
                PROJECT_FILENAME: replace(
                    self.store.load_project(self.project.project_id),
                    title="Replacement",
                    updated_at=utc_now_iso(),
                ).to_dict()
            },
        )

        history = replacement.history
        self.assertEqual(
            [entry.transaction_id for entry in history.entries],
            [first.transaction_id, replacement.transaction_id],
        )
        self.assertFalse(history.can_redo)
        with self.assertRaises(NothingToRedo):
            uow.redo(self.project.project_id)

    def test_transaction_history_survives_archive_round_trip(self) -> None:
        committed = ProjectUnitOfWork(self.store).commit(
            self.project.project_id,
            command="production.archive_round_trip",
            documents=self._documents(title="Archived Transaction"),
        )
        archive = Path(self.tmp.name) / "transactional.uvproj.zip"
        export_project(self.store, self.project.project_id, archive)

        imported_store = ProjectStore(Path(self.tmp.name) / "imported")
        imported = import_project(imported_store, archive)
        history = ProjectUnitOfWork(imported_store).history(imported.project_id)
        self.assertEqual(history.current_transaction_id, committed.transaction_id)
        self.assertTrue(history.can_undo)

        ProjectUnitOfWork(imported_store).undo(imported.project_id)
        self.assertEqual(imported_store.load_project(imported.project_id).artifacts, ())
        self.assertEqual(TimelineStore(imported_store).load(imported.project_id).tracks, ())

    def test_project_only_commit_cannot_orphan_existing_timeline_reference(self) -> None:
        uow = ProjectUnitOfWork(self.store)
        uow.commit(
            self.project.project_id,
            command="production.bind_asset",
            documents=self._documents(),
        )
        project_path = self.store.project_path(self.project.project_id)
        before = project_path.read_bytes()
        without_asset = replace(
            self.store.load_project(self.project.project_id),
            artifacts=(),
            updated_at=utc_now_iso(),
        )

        with self.assertRaisesRegex(ProjectTransactionError, "not registered"):
            uow.commit(
                self.project.project_id,
                command="project.remove_asset",
                documents={PROJECT_FILENAME: without_asset.to_dict()},
            )

        self.assertEqual(project_path.read_bytes(), before)
        self.assertEqual(uow.history(self.project.project_id).cursor, 1)

    def test_redo_revalidates_timeline_against_current_project_references(self) -> None:
        self.store.update_project(self.project.project_id, artifacts=(self.asset,))
        uow = ProjectUnitOfWork(self.store)
        uow.commit(
            self.project.project_id,
            command="timeline.bind_asset",
            documents={MAIN_TIMELINE_PATH: self.timeline.to_dict()},
        )
        uow.undo(self.project.project_id)
        self.store.update_project(self.project.project_id, artifacts=())

        with self.assertRaisesRegex(ProjectTransactionError, "not registered"):
            uow.redo(self.project.project_id)

        self.assertEqual(uow.history(self.project.project_id).cursor, 0)
        self.assertEqual(TimelineStore(self.store).load(self.project.project_id).tracks, ())


if __name__ == "__main__":
    unittest.main()
