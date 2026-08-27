from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from uv_studio.agent import (
    AgentHarness,
    AgentPlanningError,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
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


class AgentStage16GenerationTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 deferred generation target",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_generation_target",
        )
        ProductionSemanticService(self.store).create_scene(
            self.project.project_id,
            scene_id="scene_generation_target",
            title="Generation target scene",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _registry() -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Deferred Shot target regression capability.",
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
            "stage16_target_generator",
            "Stage-16 target generator",
            "Local test transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage16_target_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage16_target_generator",
                title="Stage-16 target generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available for deferred target proof.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage16_target",
                    title="UV Stage-16 Target Image",
                    description="Named model for deferred Shot target proof.",
                    capability_id="image.generate",
                    offer_id="stage16_target_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def test_generation_uses_input_shot_after_dependency_creates_it(self) -> None:
        harness = AgentHarness(self.store, self._registry())
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Create the Shot first, then submit generation into it",
            proposals=(
                AgentPlanStepProposal(
                    step_id="create_shot",
                    action_id="production.create_shot",
                    inputs={
                        "shot_id": "shot_deferred_generation",
                        "scene_id": "scene_generation_target",
                        "intent": "Created by the preceding Agent Task",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="generate",
                    action_id="generation.submit",
                    dependencies=("create_shot",),
                    inputs={
                        "shot_id": "shot_deferred_generation",
                        "model_id": "uv.image.stage16_target",
                        "inputs": {"prompt": "deferred shot target"},
                        "contract": GenerationContract().to_dict(),
                        "idempotency_key": "idem_stage16_deferred_generation",
                    },
                ),
            ),
            plan_id="agent_plan_deferred_generation_target",
        )

        self.assertIsNone(state.plan.task("generate").target_shot_id)
        self.assertNotIn("shot_deferred_generation", state.plan.canonical_references)

        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="create_shot",
        )
        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="generate",
        )

        final = coordinator.state(self.project.project_id, state.plan.plan_id)
        generated = next(task for task in final.tasks if task.task_id == "generate")
        self.assertEqual(generated.status, AgentTaskStatus.SUCCEEDED)

        generation_traces = [
            trace
            for trace in harness.traces.list(self.project.project_id)
            if trace.action_id == "generation.submit"
        ]
        self.assertEqual(len(generation_traces), 1)
        trace = generation_traces[0]
        self.assertEqual(trace.status, AgentTraceStatus.SUCCEEDED)
        self.assertIn(self.project.project_id, trace.canonical_references)
        self.assertIn("shot_deferred_generation", trace.canonical_references)
        self.assertIn(generated.result_references["job_id"], trace.canonical_references)

    def test_planner_rejects_explicit_generation_target_that_differs_from_input_shot(self) -> None:
        production = ProductionSemanticService(self.store)
        production.create_shot(
            self.project.project_id,
            shot_id="shot_generation_context",
            scene_id="scene_generation_target",
            intent="Explicit context target",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_generation_job",
            scene_id="scene_generation_target",
            intent="Generation Job target",
        )

        harness = AgentHarness(self.store, self._registry())
        coordinator = AgentTaskCoordinator(harness)
        plan_id = "agent_plan_divergent_generation_target"

        with self.assertRaisesRegex(
            AgentPlanningError,
            "target_shot_id must match inputs",
        ):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Do not let context and generation target diverge",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="generate",
                        action_id="generation.submit",
                        target_shot_id="shot_generation_context",
                        inputs={
                            "shot_id": "shot_generation_job",
                            "model_id": "uv.image.stage16_target",
                            "inputs": {"prompt": "divergent target"},
                            "contract": GenerationContract().to_dict(),
                            "idempotency_key": "idem_stage16_divergent_generation_target",
                        },
                    ),
                ),
                plan_id=plan_id,
            )

        self.assertNotIn(
            plan_id,
            {plan.plan_id for plan in coordinator.plans.list(self.project.project_id)},
        )

    def test_runtime_rejects_legacy_generation_task_with_divergent_target(self) -> None:
        malformed = SimpleNamespace(
            action_id="generation.submit",
            target_shot_id="shot_generation_context",
            inputs={"shot_id": "shot_generation_job"},
        )
        with self.assertRaisesRegex(
            AgentTaskStateError,
            "target Shot does not match its input Shot",
        ):
            AgentTaskCoordinator._execution_target_shot_id(malformed)


if __name__ == "__main__":
    unittest.main()
