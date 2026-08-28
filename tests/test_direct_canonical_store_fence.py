from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.production_state import ProductionDocumentStore
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore
from uv_studio.projects.timeline import TimelineDocument, TimelineStore


class DirectCanonicalStoreFenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.root)
        self.project = self.store.create_project(
            title="Direct canonical store fence",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_direct_canonical_store_fence",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _assert_writer_waits_for_shared_project_fence(self, writer) -> None:
        started = threading.Event()
        finished = threading.Event()
        errors: list[BaseException] = []

        def run_writer() -> None:
            started.set()
            try:
                writer()
            except BaseException as exc:  # pragma: no cover - parent assertion reports it
                errors.append(exc)
            finally:
                finished.set()

        thread = threading.Thread(target=run_writer, daemon=True)
        with ProjectTaskRecordStore(self.store).project_lock(self.project.project_id):
            thread.start()
            self.assertTrue(started.wait(timeout=2.0))
            self.assertFalse(
                finished.wait(timeout=0.2),
                "direct canonical writer entered while another runtime owned the shared project fence",
            )

        thread.join(timeout=3.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_direct_timeline_save_uses_shared_project_fence(self) -> None:
        other = TimelineStore(ProjectStore(self.root))
        self._assert_writer_waits_for_shared_project_fence(
            lambda: other.save(self.project.project_id, TimelineDocument())
        )
        path = other.project_store.resolve_project_file(
            self.project.project_id,
            "timeline/main.json",
            must_exist=True,
            allowed_roots=("timeline",),
        )
        self.assertTrue(path.is_file())

    def test_direct_production_document_save_uses_shared_project_fence(self) -> None:
        other = ProductionDocumentStore(ProjectStore(self.root))
        payload = {"schema_version": 1, "kind": "fence_probe"}
        self._assert_writer_waits_for_shared_project_fence(
            lambda: other.save(self.project.project_id, "fence_probe", payload)
        )
        self.assertEqual(
            other.load(self.project.project_id, "fence_probe"),
            payload,
        )

    def test_every_timeline_json_atomic_writer_uses_shared_project_fence(self) -> None:
        other = ProjectStore(self.root)
        path = other.resolve_project_file(
            self.project.project_id,
            "timeline/freshness-probe.json",
            allowed_roots=("timeline",),
        )
        self._assert_writer_waits_for_shared_project_fence(
            lambda: other._atomic_write_json(path, {"schema_version": 1, "kind": "probe"})
        )
        self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
