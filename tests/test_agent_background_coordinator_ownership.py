from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentBackgroundError,
    AgentBackgroundTaskCoordinator,
    AgentBackgroundWorker,
    AgentHarness,
    AgentPlanStepProposal,
    AgentSubagentTaskCoordinator,
    AgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentBackgroundCoordinatorOwnershipTests(unittest.TestCase):
    def test_other_coordinators_cannot_replace_background_harness_fences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "projects")
            project = store.create_project(
                title="Stage 18 coordinator ownership",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage18_coordinator_ownership",
            )
            harness = AgentHarness(store, ModelRegistry(CapabilityRegistry()))
            first = AgentBackgroundTaskCoordinator(harness)
            production_fence = harness.production.uow
            timeline_fence = harness.timeline.unit_of_work
            generation_fence = harness.generation

            with self.assertRaisesRegex(
                AgentBackgroundError,
                "already has an AgentBackgroundTaskCoordinator",
            ):
                AgentBackgroundTaskCoordinator(harness)

            for coordinator_type in (AgentTaskCoordinator, AgentSubagentTaskCoordinator):
                with self.subTest(coordinator_type=coordinator_type.__name__):
                    with self.assertRaisesRegex(
                        AgentTaskStateError,
                        "owned by an AgentBackgroundTaskCoordinator",
                    ):
                        coordinator_type(harness)
                    self.assertIs(harness.production.uow, production_fence)
                    self.assertIs(harness.timeline.unit_of_work, timeline_fence)
                    self.assertIs(harness.generation, generation_fence)

            state = first.create_plan(
                project_id=project.project_id,
                goal="Prove the original coordinator still owns the harness fences",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={
                            "scene_id": "scene_original_coordinator",
                            "title": "Original coordinator",
                        },
                    ),
                ),
                plan_id="agent_plan_coordinator_ownership",
            )
            worker = AgentBackgroundWorker(
                first,
                worker_id="worker_original_coordinator",
                lease_seconds=10,
                heartbeat_seconds=0,
            )
            worker.run_once(
                project_id=project.project_id,
                plan_id=state.plan.plan_id,
            )

            reopened = first.state(project.project_id, state.plan.plan_id)
            self.assertEqual(reopened.tasks[0].status, AgentTaskStatus.SUCCEEDED)
            production = ProductionSemanticService(store).state(project.project_id)
            self.assertEqual(
                production.scene("scene_original_coordinator").title,
                "Original coordinator",
            )


if __name__ == "__main__":
    unittest.main()
