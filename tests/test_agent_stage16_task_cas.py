from __future__ import annotations

import tempfile
import unittest
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
from uv_studio.projects.store import ProjectStore


class AgentStage16TaskCompareAndSwapTests(unittest.TestCase):
    def test_stale_ready_snapshot_cannot_overwrite_running_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(
                title="Stage 16 task compare and swap",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage16_task_cas",
            )
            harness = AgentHarness(store, ModelRegistry(CapabilityRegistry()))
            coordinator = AgentTaskCoordinator(harness)
            state = coordinator.create_plan(
                project_id=project.project_id,
                goal="Reject a stale concurrent task transition",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_cas", "title": "CAS scene"},
                    ),
                ),
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

    def test_fresh_snapshot_can_take_valid_followup_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(
                title="Stage 16 fresh task transition",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage16_fresh_transition",
            )
            harness = AgentHarness(store, ModelRegistry(CapabilityRegistry()))
            coordinator = AgentTaskCoordinator(harness)
            state = coordinator.create_plan(
                project_id=project.project_id,
                goal="Keep valid fresh transitions working",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_fresh", "title": "Fresh scene"},
                    ),
                ),
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
