from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanningError,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class AgentStage16CanonicalPrerequisiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 16 canonical prerequisites",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_canonical_prerequisites",
        )
        source_path = self.store.resolve_project_file(
            self.project.project_id,
            "sources/source_video.mp4",
            allowed_roots=("sources",),
        )
        source_path.write_bytes(b"video")
        self.video = ProjectReference(
            id="source_video",
            kind="video",
            path="sources/source_video.mp4",
            metadata={"duration_us": 20_000_000},
        )
        self.store.update_project(
            self.project.project_id,
            sources=(self.video,),
        )

        self.production = ProductionSemanticService(self.store)
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_existing",
            title="Existing",
        )
        self.production.create_shot(
            self.project.project_id,
            shot_id="shot_existing",
            scene_id="scene_existing",
            intent="Existing shot",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    def _coordinator(self) -> AgentTaskCoordinator:
        return AgentTaskCoordinator(AgentHarness(self.store, self._registry()))

    def _assert_plan_absent(self, coordinator: AgentTaskCoordinator, plan_id: str) -> None:
        self.assertNotIn(
            plan_id,
            {plan.plan_id for plan in coordinator.plans.list(self.project.project_id)},
        )

    def test_missing_scene_is_rejected_before_plan_persistence(self) -> None:
        coordinator = self._coordinator()
        plan_id = "agent_plan_missing_scene_prerequisite"
        with self.assertRaisesRegex(
            AgentPlanningError,
            "scene_id.*exist or be created by its dependency closure",
        ):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Reject a Shot whose Scene cannot exist before execution",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="shot",
                        action_id="production.create_shot",
                        inputs={
                            "shot_id": "shot_missing_scene",
                            "scene_id": "scene_missing",
                            "intent": "Impossible prerequisite",
                        },
                    ),
                ),
                plan_id=plan_id,
            )
        self._assert_plan_absent(coordinator, plan_id)

    def test_dependency_closure_can_provision_scene_shot_take_track_and_clip(self) -> None:
        coordinator = self._coordinator()
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Use only dependency-provided canonical prerequisites",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_chain", "title": "Chain"},
                ),
                AgentPlanStepProposal(
                    step_id="shot",
                    action_id="production.create_shot",
                    dependencies=("scene",),
                    inputs={
                        "shot_id": "shot_chain",
                        "scene_id": "scene_chain",
                        "intent": "Dependency-created Scene",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="take",
                    action_id="production.register_take",
                    dependencies=("shot",),
                    inputs={
                        "take_id": "take_chain",
                        "shot_id": "shot_chain",
                        "reference_id": self.video.id,
                    },
                ),
                AgentPlanStepProposal(
                    step_id="accept",
                    action_id="production.accept_take",
                    dependencies=("take",),
                    inputs={
                        "take_id": "take_chain",
                        "timeline_start_us": 0,
                        "duration_us": 3_000_000,
                        "track_id": "trk_chain",
                        "clip_id": "clip_chain_a",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="add_clip",
                    action_id="timeline.add_clip",
                    dependencies=("accept",),
                    inputs={
                        "track_id": "trk_chain",
                        "reference_id": self.video.id,
                        "timeline_start_us": 5_000_000,
                        "duration_us": 2_000_000,
                        "clip_id": "clip_chain_b",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="move_clip",
                    action_id="timeline.move_clip",
                    dependencies=("add_clip",),
                    inputs={
                        "clip_id": "clip_chain_b",
                        "timeline_start_us": 8_000_000,
                    },
                ),
            ),
            plan_id="agent_plan_dependency_prerequisites",
        )

        self.assertEqual(state.plan.task("shot").dependencies, ("scene",))
        self.assertEqual(state.plan.task("take").dependencies, ("shot",))
        self.assertEqual(state.plan.task("accept").dependencies, ("take",))
        self.assertEqual(state.plan.task("add_clip").dependencies, ("accept",))
        self.assertEqual(state.plan.task("move_clip").dependencies, ("add_clip",))

    def test_duplicate_existing_and_planned_outputs_are_rejected(self) -> None:
        coordinator = self._coordinator()

        existing_plan = "agent_plan_existing_shot_duplicate"
        with self.assertRaisesRegex(AgentPlanningError, "shot already exists"):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Reject an existing Shot identity",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="duplicate_shot",
                        action_id="production.create_shot",
                        inputs={
                            "shot_id": "shot_existing",
                            "scene_id": "scene_existing",
                            "intent": "Duplicate",
                        },
                    ),
                ),
                plan_id=existing_plan,
            )
        self._assert_plan_absent(coordinator, existing_plan)

        planned_plan = "agent_plan_planned_scene_duplicate"
        with self.assertRaisesRegex(AgentPlanningError, "duplicate scene identity"):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Reject duplicate planned Scene producers",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene_a",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_duplicate", "title": "A"},
                    ),
                    AgentPlanStepProposal(
                        step_id="scene_b",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_duplicate", "title": "B"},
                    ),
                ),
                plan_id=planned_plan,
            )
        self._assert_plan_absent(coordinator, planned_plan)

    def test_missing_take_track_clip_and_media_are_rejected(self) -> None:
        cases = (
            (
                "agent_plan_missing_take_prerequisite",
                "take_id.*exist or be created by its dependency closure",
                AgentPlanStepProposal(
                    step_id="accept",
                    action_id="production.accept_take",
                    inputs={
                        "take_id": "take_missing",
                        "timeline_start_us": 0,
                        "duration_us": 1_000_000,
                    },
                ),
            ),
            (
                "agent_plan_missing_track_prerequisite",
                "track_id.*exist or be created by its dependency closure",
                AgentPlanStepProposal(
                    step_id="add",
                    action_id="timeline.add_clip",
                    inputs={
                        "track_id": "trk_missing",
                        "reference_id": self.video.id,
                        "timeline_start_us": 0,
                        "duration_us": 1_000_000,
                        "clip_id": "clip_missing_track",
                    },
                ),
            ),
            (
                "agent_plan_missing_clip_prerequisite",
                "clip_id.*exist or be created by its dependency closure",
                AgentPlanStepProposal(
                    step_id="move",
                    action_id="timeline.move_clip",
                    inputs={"clip_id": "clip_missing", "timeline_start_us": 1_000_000},
                ),
            ),
            (
                "agent_plan_missing_media_prerequisite",
                "media reference.*registered",
                AgentPlanStepProposal(
                    step_id="take",
                    action_id="production.register_take",
                    inputs={
                        "take_id": "take_missing_media",
                        "shot_id": "shot_existing",
                        "reference_id": "source_missing",
                    },
                ),
            ),
        )

        for plan_id, pattern, proposal in cases:
            with self.subTest(plan_id=plan_id):
                coordinator = self._coordinator()
                with self.assertRaisesRegex(AgentPlanningError, pattern):
                    coordinator.create_plan(
                        project_id=self.project.project_id,
                        goal="Reject a missing canonical prerequisite",
                        proposals=(proposal,),
                        plan_id=plan_id,
                    )
                self._assert_plan_absent(coordinator, plan_id)


if __name__ == "__main__":
    unittest.main()
