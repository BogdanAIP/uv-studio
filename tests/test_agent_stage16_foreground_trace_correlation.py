from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentStage16ForegroundTraceCorrelationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 foreground trace correlation",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_foreground_trace_correlation",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _empty_registry() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    def test_task_completion_ignores_newer_uncorrelated_trace_for_same_action(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        raw_trace_store = harness.traces
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Create the task-owned scene",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_task_owned",
                        "title": "Task-owned scene",
                    },
                ),
            ),
            plan_id="agent_plan_foreground_trace_correlation",
        )

        original_execute = harness.execute
        injected: dict[str, str] = {}

        def execute_with_newer_uncorrelated_trace(
            *,
            project_id: str,
            action_id: str,
            inputs: dict[str, Any],
            target_shot_id: str | None = None,
        ) -> Any:
            result = original_execute(
                project_id=project_id,
                action_id=action_id,
                inputs=inputs,
                target_shot_id=target_shot_id,
            )
            correlated = [
                trace
                for trace in raw_trace_store.list(project_id)
                if trace.action_id == action_id
                and any(
                    reference.startswith("agent_corr_")
                    for reference in trace.canonical_references
                )
            ]
            self.assertEqual(len(correlated), 1)
            task_trace = correlated[0]

            # Simulate a separate Stage-15 harness that writes the same action after
            # this task's trace. It deliberately carries the same action/input digest
            # and even the untyped plan/task references, but not the opaque typed
            # agent_corr_* reference owned by this task.
            unrelated_references = tuple(
                dict.fromkeys(
                    (
                        *(
                            reference
                            for reference in task_trace.canonical_references
                            if not reference.startswith("agent_corr_")
                        ),
                        "scene_unrelated",
                    )
                )
            )
            unrelated = replace(
                task_trace,
                trace_id="agent_trace_unrelated_same_action",
                created_at="9999-12-31T23:59:59+00:00",
                canonical_references=unrelated_references,
            )
            raw_trace_store.append(unrelated)
            injected["trace_id"] = unrelated.trace_id
            return result

        harness.execute = execute_with_newer_uncorrelated_trace  # type: ignore[method-assign]

        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )

        task = coordinator.tasks.get(
            self.project.project_id,
            state.plan.plan_id,
            "scene",
        )
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertNotEqual(task.trace_id, injected["trace_id"])
        self.assertIn("scene_task_owned", task.canonical_references)
        self.assertNotIn("scene_unrelated", task.canonical_references)

        selected = next(
            trace
            for trace in raw_trace_store.list(self.project.project_id)
            if trace.trace_id == task.trace_id
        )
        self.assertTrue(
            any(
                reference.startswith("agent_corr_")
                for reference in selected.canonical_references
            )
        )
        self.assertEqual(selected.input_digest, coordinator._expected_input_digest(state.plan.task("scene")))


if __name__ == "__main__":
    unittest.main()
