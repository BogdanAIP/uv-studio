from __future__ import annotations

import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore


class ProjectStoreCrossRuntimeFenceTests(unittest.TestCase):
    def test_update_project_waits_for_shared_canonical_fence_and_preserves_both_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            store_a = ProjectStore(root)
            project = store_a.create_project(
                title="Original",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_project_document_fence",
            )
            store_b = ProjectStore(root)
            stale_for_canonical_writer = store_a.load_project(project.project_id)

            update_started = threading.Event()
            update_finished = threading.Event()
            update_errors: list[BaseException] = []

            def user_update() -> None:
                update_started.set()
                try:
                    store_b.update_project(
                        project.project_id,
                        settings={"user_edit": True},
                    )
                except BaseException as exc:  # pragma: no cover - surfaced below
                    update_errors.append(exc)
                finally:
                    update_finished.set()

            task_records = ProjectTaskRecordStore(store_a)
            with task_records.project_lock(project.project_id):
                thread = threading.Thread(target=user_update, daemon=True)
                thread.start()
                self.assertTrue(update_started.wait(timeout=2))
                self.assertFalse(
                    update_finished.wait(timeout=0.2),
                    "update_project bypassed the shared cross-runtime project fence",
                )

                store_a.save_project(
                    replace(stale_for_canonical_writer, title="Canonical command edit")
                )

            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(update_errors, [])

            final = store_a.load_project(project.project_id)
            self.assertEqual(final.title, "Canonical command edit")
            self.assertEqual(final.settings, {"user_edit": True})


if __name__ == "__main__":
    unittest.main()
