from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentPlanner,
    AgentPlanningError,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentStage16PlannerTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 16 planner targets",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_planner_targets",
        )
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_targets",
            title="Target scene",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_target_a",
            scene_id="scene_targets",
            intent="First planner target",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_target_b",
            scene_id="scene_targets",
            intent="Second planner target",
        )
        self.harness = AgentHarness(
            self.store,
            ModelRegistry(CapabilityRegistry()),
        )
        self.planner = AgentPlanner(self.harness)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _proposal(step_id: str, scene_id: str, target_shot_id: str) -> AgentPlanStepProposal:
        return AgentPlanStepProposal(
            step_id=step_id,
            action_id="production.create_scene",
            inputs={"scene_id": scene_id, "title": scene_id},
            target_shot_id=target_shot_id,
        )

    def test_proposal_specific_missing_target_is_rejected_during_planning(self) -> None:
        with self.assertRaisesRegex(AgentPlanningError, "could not bind target shot"):
            self.planner.build(
                project_id=self.project.project_id,
                goal="Reject a missing proposal target before durable plan creation",
                proposals=(
                    self._proposal(
                        "missing_target",
                        "scene_missing_target",
                        "shot_does_not_exist",
                    ),
                ),
                plan_id="agent_plan_missing_proposal_target",
            )

    def test_distinct_effective_targets_are_bound_into_plan_context(self) -> None:
        proposals = (
            self._proposal("target_a", "scene_for_a", "shot_target_a"),
            self._proposal("target_b", "scene_for_b", "shot_target_b"),
        )
        first = self.planner.build(
            project_id=self.project.project_id,
            goal="Bind every proposal-specific target",
            proposals=proposals,
            plan_id="agent_plan_target_binding_a",
        )
        second = self.planner.build(
            project_id=self.project.project_id,
            goal="Bind every proposal-specific target",
            proposals=proposals,
            plan_id="agent_plan_target_binding_b",
        )

        self.assertIn(self.project.project_id, first.canonical_references)
        self.assertIn("shot_target_a", first.canonical_references)
        self.assertIn("shot_target_b", first.canonical_references)
        self.assertEqual(first.context_digest, second.context_digest)
        self.assertEqual(
            tuple(task.target_shot_id for task in first.tasks),
            ("shot_target_a", "shot_target_b"),
        )
        project_only = self.harness.context.build(self.project.project_id)
        self.assertNotEqual(first.context_digest, project_only.digest)


if __name__ == "__main__":
    unittest.main()
