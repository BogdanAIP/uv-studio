from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStatus,
    AgentTraceRecord,
    AgentTraceStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class _PersistThenFailTraceStore:
    """Simulate a durable append whose caller still observes an I/O error."""

    def __init__(self, base: Any, *, action_id: str, error: BaseException) -> None:
        self._base = base
        self._action_id = action_id
        self._error = error

    def append(self, record: AgentTraceRecord):
        result = self._base.append(record)
        if (
            record.status is AgentTraceStatus.SUCCEEDED
            and record.action_id == self._action_id
        ):
            raise self._error
        return result

    def list(self, project_id: str):
        return self._base.list(project_id)


class AgentStage16PostAppendTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 post-append trace",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_post_append_trace",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _empty_registry() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    def test_durable_success_trace_wins_over_post_append_error(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _PersistThenFailTraceStore(
            harness.traces,
            action_id="production.create_scene",
            error=OSError("simulated error after durable success trace append"),
        )
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Keep durable task state aligned with the persisted success trace",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_post_append",
                        "title": "Persisted success",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="shot",
                    action_id="production.create_shot",
                    dependencies=("scene",),
                    inputs={
                        "shot_id": "shot_post_append",
                        "scene_id": "scene_post_append",
                        "intent": "Unlocked only after durable scene success",
                    },
                ),
            ),
            plan_id="agent_plan_post_append_trace",
        )
        initial = {task.task_id: task for task in state.tasks}
        self.assertEqual(initial["scene"].status, AgentTaskStatus.READY)
        self.assertEqual(initial["shot"].status, AgentTaskStatus.PLANNED)

        with self.assertRaisesRegex(OSError, "after durable success trace append"):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        durable = {
            task.task_id: task
            for task in coordinator.tasks.list_by_plan(
                self.project.project_id,
                state.plan.plan_id,
            )
        }
        self.assertEqual(durable["scene"].status, AgentTaskStatus.SUCCEEDED)
        self.assertIsNotNone(durable["scene"].trace_id)
        self.assertEqual(durable["shot"].status, AgentTaskStatus.READY)
        self.assertEqual(
            ProductionSemanticService(self.store)
            .state(self.project.project_id)
            .scene("scene_post_append")
            .title,
            "Persisted success",
        )

        traces = harness.traces.list(self.project.project_id)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].status, AgentTraceStatus.SUCCEEDED)
        self.assertEqual(durable["scene"].trace_id, traces[0].trace_id)

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        reopened_tasks = {task.task_id: task for task in reopened.tasks}
        self.assertEqual(reopened_tasks["scene"].status, AgentTaskStatus.SUCCEEDED)
        self.assertEqual(reopened_tasks["shot"].status, AgentTaskStatus.READY)
        self.assertEqual(len(reopened_harness.traces.list(self.project.project_id)), 1)


if __name__ == "__main__":
    unittest.main()
