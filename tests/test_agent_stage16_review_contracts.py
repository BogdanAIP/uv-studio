from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanningError,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
    AgentTaskStore,
    AgentTraceStatus,
)
from uv_studio.capabilities.models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityEffects,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import GenerationContract, ModelDefinition, ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentStage16ReviewContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 review contracts",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_review_contracts",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _empty_registry() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    @staticmethod
    def _generation_registry() -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Stage-16 deferred target validation capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
            effects=CapabilityEffects(
                mutates_project=True,
                generates_media=True,
                long_running=True,
                reversible=False,
            ),
        )
        adapter = AdapterDefinition(
            "stage16_review_generator",
            "Stage-16 review generator",
            "Local test transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage16_review_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage16_review_generator",
                title="Stage-16 review generation",
                availability=OfferAvailability.AVAILABLE,
                reason="Available for review contract proof.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage16_review",
                    title="UV Stage-16 Review Image",
                    description="Named model for deferred target validation.",
                    capability_id="image.generate",
                    offer_id="stage16_review_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def test_exported_task_store_rejects_untyped_unrelated_trace(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentTaskCoordinator(harness)
        self.assertIsInstance(coordinator.tasks, AgentTaskStore)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Do not accept unrelated trace provenance",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_planned", "title": "Planned"},
                ),
            ),
            plan_id="agent_plan_trace_provenance",
        )
        running = coordinator.tasks.transition(
            state.tasks[0],
            AgentTaskStatus.RUNNING,
        )

        harness.execute(
            project_id=self.project.project_id,
            action_id="production.create_scene",
            inputs={"scene_id": "scene_unrelated", "title": "Unrelated"},
        )
        unrelated = harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(unrelated.status, AgentTraceStatus.SUCCEEDED)

        with self.assertRaisesRegex(AgentTaskStateError, "typed task correlation"):
            coordinator.tasks.transition(
                running,
                AgentTaskStatus.SUCCEEDED,
                trace=unrelated,
            )

        durable = coordinator.tasks.get(
            self.project.project_id,
            state.plan.plan_id,
            "scene",
        )
        self.assertEqual(durable.status, AgentTaskStatus.RUNNING)
        self.assertIsNone(durable.trace_id)
        self.assertNotIn("scene_unrelated", durable.canonical_references)

    def test_exported_task_store_rejects_failed_trace_as_success(self) -> None:
        production = ProductionSemanticService(self.store)
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Match terminal task and trace statuses",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_status_match", "title": "Planned"},
                ),
            ),
            plan_id="agent_plan_trace_status",
        )
        running = coordinator.tasks.transition(
            state.tasks[0],
            AgentTaskStatus.RUNNING,
        )
        production.create_scene(
            self.project.project_id,
            scene_id="scene_status_match",
            title="Already exists",
        )
        spec = state.plan.task("scene")
        with coordinator._correlated_traces.correlate(
            state.plan.plan_id,
            spec.task_id,
            spec.skill_id,
            expected_input_digest=coordinator._expected_input_digest(spec),
        ):
            with self.assertRaises(Exception):
                harness.execute(
                    project_id=self.project.project_id,
                    action_id=spec.action_id,
                    inputs=spec.inputs,
                )
        failed_trace = harness.traces.list(self.project.project_id)[-1]
        self.assertEqual(failed_trace.status, AgentTraceStatus.FAILED)

        with self.assertRaisesRegex(AgentTaskStateError, "does not match"):
            coordinator.tasks.transition(
                running,
                AgentTaskStatus.SUCCEEDED,
                trace=failed_trace,
            )
        self.assertEqual(
            coordinator.tasks.get(
                self.project.project_id,
                state.plan.plan_id,
                "scene",
            ).status,
            AgentTaskStatus.RUNNING,
        )

    def test_planner_rejects_missing_generation_shot_without_creator_dependency(self) -> None:
        harness = AgentHarness(self.store, self._generation_registry())
        coordinator = AgentTaskCoordinator(harness)
        plan_id = "agent_plan_missing_generation_shot"

        with self.assertRaisesRegex(
            AgentPlanningError,
            "already exist or be created",
        ):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Reject an unresolvable generation target",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="generate",
                        action_id="generation.submit",
                        inputs={
                            "shot_id": "shot_missing_generation",
                            "model_id": "uv.image.stage16_review",
                            "inputs": {"prompt": "missing target"},
                            "contract": GenerationContract().to_dict(),
                            "idempotency_key": "idem_stage16_missing_generation",
                        },
                    ),
                ),
                plan_id=plan_id,
            )

        self.assertNotIn(
            plan_id,
            {plan.plan_id for plan in coordinator.plans.list(self.project.project_id)},
        )

    def test_planner_allows_transitive_dependency_to_create_generation_shot(self) -> None:
        ProductionSemanticService(self.store).create_scene(
            self.project.project_id,
            scene_id="scene_generation_parent",
            title="Generation parent",
        )
        harness = AgentHarness(self.store, self._generation_registry())
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Allow a transitive dependency to create the generation Shot",
            proposals=(
                AgentPlanStepProposal(
                    step_id="create_shot",
                    action_id="production.create_shot",
                    inputs={
                        "shot_id": "shot_transitive_generation",
                        "scene_id": "scene_generation_parent",
                        "intent": "Created before generation",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="barrier",
                    action_id="production.create_scene",
                    dependencies=("create_shot",),
                    inputs={
                        "scene_id": "scene_generation_barrier",
                        "title": "Dependency barrier",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="generate",
                    action_id="generation.submit",
                    dependencies=("barrier",),
                    inputs={
                        "shot_id": "shot_transitive_generation",
                        "model_id": "uv.image.stage16_review",
                        "inputs": {"prompt": "transitive target"},
                        "contract": GenerationContract().to_dict(),
                        "idempotency_key": "idem_stage16_transitive_generation",
                    },
                ),
            ),
            plan_id="agent_plan_transitive_generation_shot",
        )

        self.assertIsNone(state.plan.task("generate").target_shot_id)
        self.assertEqual(
            state.plan.task("generate").dependencies,
            ("barrier",),
        )


if __name__ == "__main__":
    unittest.main()
