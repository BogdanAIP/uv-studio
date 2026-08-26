from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import utc_now_iso
from uv_studio.projects.store import ProjectStore


class AgentStage16TaskCompareAndSwapTests(unittest.TestCase):
    @staticmethod
    def _coordinator(store: ProjectStore) -> AgentTaskCoordinator:
        return AgentTaskCoordinator(
            AgentHarness(store, ModelRegistry(CapabilityRegistry()))
        )

    def _create_plan(self, projects_root: Path, *, project_id: str, plan_id: str):
        store = ProjectStore(projects_root)
        project = store.create_project(
            title="Stage 16 task compare and swap",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id=project_id,
        )
        coordinator = self._coordinator(store)
        state = coordinator.create_plan(
            project_id=project.project_id,
            goal="Reject stale durable task transitions",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={"scene_id": f"scene_{project_id}", "title": "CAS scene"},
                ),
            ),
            plan_id=plan_id,
        )
        return store, project, coordinator, state

    def test_stale_ready_snapshot_cannot_overwrite_running_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, project, coordinator, state = self._create_plan(
                Path(tmp) / "projects",
                project_id="prj_stage16_task_cas",
                plan_id="agent_plan_task_cas",
            )
            first_ready = state.tasks[0]
            stale_ready = coordinator.tasks.get(
                project.project_id,
                state.plan.plan_id,
                first_ready.task_id,
            )
            self.assertEqual(first_ready, stale_ready)

            running = coordinator.tasks.transition(first_ready, AgentTaskStatus.RUNNING)
            self.assertEqual(running.status, AgentTaskStatus.RUNNING)
            self.assertIsNotNone(running.started_at)

            with self.assertRaisesRegex(AgentTaskStateError, "stale Agent Task snapshot"):
                coordinator.tasks.transition(stale_ready, AgentTaskStatus.CANCELLED)

            durable = coordinator.tasks.get(
                project.project_id,
                state.plan.plan_id,
                first_ready.task_id,
            )
            self.assertEqual(durable.status, AgentTaskStatus.RUNNING)
            self.assertEqual(durable.started_at, running.started_at)
            self.assertIsNone(durable.ended_at)
            self.assertIsNone(durable.trace_id)
            self.assertEqual(durable.updated_at, running.updated_at)

    def test_stale_snapshot_across_project_store_instances_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp) / "projects"
            _, project, first, state = self._create_plan(
                projects_root,
                project_id="prj_stage16_cross_store_cas",
                plan_id="agent_plan_cross_store_cas",
            )
            second = self._coordinator(ProjectStore(projects_root))
            first_ready = first.tasks.get(
                project.project_id,
                state.plan.plan_id,
                "scene",
            )
            second_ready = second.tasks.get(
                project.project_id,
                state.plan.plan_id,
                "scene",
            )
            self.assertEqual(first_ready, second_ready)

            running = first.tasks.transition(first_ready, AgentTaskStatus.RUNNING)
            with self.assertRaisesRegex(AgentTaskStateError, "stale Agent Task snapshot"):
                second.tasks.transition(second_ready, AgentTaskStatus.CANCELLED)

            durable = second.tasks.get(
                project.project_id,
                state.plan.plan_id,
                "scene",
            )
            self.assertEqual(durable.status, AgentTaskStatus.RUNNING)
            self.assertEqual(durable.started_at, running.started_at)

    def test_direct_write_cannot_bypass_transition_compare_and_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, project, coordinator, state = self._create_plan(
                Path(tmp) / "projects",
                project_id="prj_stage16_direct_write_guard",
                plan_id="agent_plan_direct_write_guard",
            )
            ready = state.tasks[0]
            running = coordinator.tasks.transition(ready, AgentTaskStatus.RUNNING)
            now = utc_now_iso()
            stale_cancelled = replace(
                ready,
                status=AgentTaskStatus.CANCELLED,
                updated_at=now,
                ended_at=now,
            )

            with self.assertRaisesRegex(AgentTaskStateError, "direct Agent Task writes are disabled"):
                coordinator.tasks.write(stale_cancelled)

            durable = coordinator.tasks.get(
                project.project_id,
                state.plan.plan_id,
                ready.task_id,
            )
            self.assertEqual(durable, running)

    def test_fresh_snapshot_can_take_valid_followup_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, project, coordinator, state = self._create_plan(
                Path(tmp) / "projects",
                project_id="prj_stage16_fresh_transition",
                plan_id="agent_plan_fresh_transition",
            )
            ready = state.tasks[0]
            running = coordinator.tasks.transition(ready, AgentTaskStatus.RUNNING)
            failure = AgentTaskStateError("synthetic execution failure")
            failed = coordinator.tasks.transition(
                running,
                AgentTaskStatus.FAILED,
                error=failure,
            )
            self.assertEqual(failed.status, AgentTaskStatus.FAILED)
            self.assertEqual(failed.started_at, running.started_at)
            self.assertIsNotNone(failed.ended_at)
            self.assertIn("synthetic execution failure", failed.error_message)


if __name__ == "__main__":
    unittest.main()
