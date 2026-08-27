from __future__ import annotations

import errno
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentTaskCoordinator,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.task_records import ProjectTaskRecordStore


class AgentStage16StorageLockingTests(unittest.TestCase):
    @staticmethod
    def _coordinator(store: ProjectStore) -> AgentTaskCoordinator:
        return AgentTaskCoordinator(
            AgentHarness(store, ModelRegistry(CapabilityRegistry()))
        )

    @staticmethod
    def _create_project(root: Path, project_id: str) -> ProjectStore:
        store = ProjectStore(root)
        store.create_project(
            title="Stage 16 storage locking",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id=project_id,
        )
        return store

    def test_project_lock_order_does_not_deadlock_store_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            project_id = "prj_stage16_lock_order"
            store = self._create_project(root, project_id)
            records = ProjectTaskRecordStore(store)
            holder_entered = threading.Event()
            proceed = threading.Event()
            writer_has_store = threading.Event()
            errors: list[BaseException] = []

            def holder() -> None:
                try:
                    with records.project_lock(project_id):
                        holder_entered.set()
                        if not proceed.wait(timeout=2.0):
                            raise AssertionError("lock-order test did not receive proceed signal")
                        with store._lock:
                            pass
                except BaseException as exc:  # pragma: no cover - reported by parent assertions
                    errors.append(exc)

            def writer() -> None:
                try:
                    if not holder_entered.wait(timeout=2.0):
                        raise AssertionError("project lock was not acquired")
                    with store._lock:
                        writer_has_store.set()
                        records.write(
                            project_id,
                            "lock_order_probe",
                            {"record_type": "lock_order_probe", "ok": True},
                        )
                except BaseException as exc:  # pragma: no cover - reported by parent assertions
                    errors.append(exc)

            holder_thread = threading.Thread(target=holder, daemon=True)
            writer_thread = threading.Thread(target=writer, daemon=True)
            holder_thread.start()
            self.assertTrue(holder_entered.wait(timeout=2.0))
            writer_thread.start()

            # With the canonical ProjectStore -> project-lock order, the writer
            # cannot hold ProjectStore._lock while the holder owns the project
            # lease. Under the old inverse ordering it could, creating AB/BA.
            writer_has_store.wait(timeout=0.2)
            proceed.set()
            holder_thread.join(timeout=2.0)
            writer_thread.join(timeout=2.0)

            self.assertFalse(holder_thread.is_alive(), "project-lock holder deadlocked")
            self.assertFalse(writer_thread.is_alive(), "task-record writer deadlocked")
            self.assertEqual(errors, [])
            self.assertTrue(records.path(project_id, "lock_order_probe").is_file())

    def test_same_plan_id_is_create_if_absent_across_store_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            project_id = "prj_stage16_plan_create_once"
            first_store = self._create_project(root, project_id)
            first = self._coordinator(first_store)
            second = self._coordinator(ProjectStore(root))
            plan_id = "shared_plan_create_once"
            first_plan = first.planner.build(
                project_id=project_id,
                goal="First competing plan",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_first", "title": "First"},
                    ),
                ),
                plan_id=plan_id,
            )
            second_plan = second.planner.build(
                project_id=project_id,
                goal="Second competing plan",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_second", "title": "Second"},
                    ),
                ),
                plan_id=plan_id,
            )
            barrier = threading.Barrier(2)
            outcomes: list[str] = []
            errors: list[BaseException] = []
            outcome_lock = threading.Lock()

            def append(store: AgentTaskCoordinator, plan) -> None:
                try:
                    barrier.wait(timeout=2.0)
                    store.plans.append(plan)
                except AgentPlanningError:
                    with outcome_lock:
                        outcomes.append("conflict")
                except BaseException as exc:  # pragma: no cover - reported below
                    with outcome_lock:
                        errors.append(exc)
                else:
                    with outcome_lock:
                        outcomes.append("created")

            threads = (
                threading.Thread(target=append, args=(first, first_plan), daemon=True),
                threading.Thread(target=append, args=(second, second_plan), daemon=True),
            )
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=3.0)

            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(errors, [])
            self.assertEqual(sorted(outcomes), ["conflict", "created"])
            durable = first.plans.get(project_id, plan_id)
            self.assertIn(durable.goal, {first_plan.goal, second_plan.goal})
            self.assertIn(
                durable.task("scene").inputs["scene_id"],
                {"scene_first", "scene_second"},
            )

    @unittest.skipUnless(os.name == "nt", "Windows msvcrt retry proof")
    def test_windows_project_lock_retries_beyond_ten_contentions(self) -> None:
        from uv_studio.projects import task_records

        class FakeHandle:
            def seek(self, *_args) -> None:
                return None

            def fileno(self) -> int:
                return 123

        failures = [OSError(errno.EACCES, "synthetic lock contention") for _ in range(12)]
        with mock.patch("msvcrt.locking", side_effect=[*failures, None]) as locking:
            with mock.patch.object(task_records.time, "sleep") as sleep:
                task_records._acquire_os_lock(FakeHandle())

        self.assertEqual(locking.call_count, 13)
        self.assertEqual(sleep.call_count, 12)


if __name__ == "__main__":
    unittest.main()
