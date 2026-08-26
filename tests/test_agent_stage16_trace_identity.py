from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStatus,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentStage16TraceIdentityTests(unittest.TestCase):
    def test_unrelated_trace_with_colliding_canonical_ids_cannot_complete_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp) / "projects"
            store = ProjectStore(projects_root)
            project = store.create_project(
                title="Stage 16 trace identity",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage16_trace_identity",
            )
            models = ModelRegistry(CapabilityRegistry())
            production = ProductionSemanticService(store)
            production.create_scene(
                project.project_id,
                scene_id="collision_plan",
                title="Collision scene",
            )

            harness = AgentHarness(store, models)
            coordinator = AgentTaskCoordinator(harness)
            planned = coordinator.create_plan(
                project_id=project.project_id,
                goal="Create the planned shot only",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="collision_task",
                        action_id="production.create_shot",
                        inputs={
                            "scene_id": "collision_plan",
                            "shot_id": "planned_shot",
                            "intent": "The actual planned shot",
                        },
                    ),
                ),
                plan_id="collision_plan",
            )
            coordinator.tasks.transition(planned.tasks[0], AgentTaskStatus.RUNNING)

            # This unrelated direct action deliberately creates canonical IDs equal
            # to the plan_id/task_id. Old untyped membership matching could mistake
            # this trace for completion of the planned task.
            harness.execute(
                project_id=project.project_id,
                action_id="production.create_shot",
                inputs={
                    "scene_id": "collision_plan",
                    "shot_id": "collision_task",
                    "intent": "Unrelated direct harness action",
                },
            )
            unrelated = harness.traces.list(project.project_id)[-1]
            self.assertIn("collision_plan", unrelated.canonical_references)
            self.assertIn("collision_task", unrelated.canonical_references)

            reopened_store = ProjectStore(projects_root)
            reopened_harness = AgentHarness(reopened_store, ModelRegistry(CapabilityRegistry()))
            reopened = AgentTaskCoordinator(reopened_harness)
            recovered = reopened.state(project.project_id, planned.plan.plan_id)
            task = recovered.tasks[0]

            self.assertEqual(task.status, AgentTaskStatus.FAILED)
            self.assertEqual(recovered.status, AgentPlanStatus.FAILED)
            self.assertIsNone(task.trace_id)
            self.assertIn("interrupted", task.error_message.lower())
            self.assertEqual(len(reopened_harness.traces.list(project.project_id)), 1)


if __name__ == "__main__":
    unittest.main()
