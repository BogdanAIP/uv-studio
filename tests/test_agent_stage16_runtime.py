from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentSkillCatalog,
    AgentTaskCoordinator,
    AgentTaskStatus,
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


class AgentStage16RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 16 runtime",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_runtime",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _local_generation_registry() -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Stage-16 runtime proof capability.",
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
            "stage16_runtime_generator",
            "Stage 16 runtime generator",
            "Local bounded test transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage16_runtime_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage16_runtime_generator",
                title="Stage 16 local generation",
                availability=OfferAvailability.AVAILABLE,
                reason="Available for Stage-16 runtime proof.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage16_runtime",
                    title="UV Stage 16 Runtime Image",
                    description="Named local model for coordinator proof.",
                    capability_id="image.generate",
                    offer_id="stage16_runtime_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def test_skill_execution_correlates_plan_task_and_skill_in_stage15_trace(self) -> None:
        harness = AgentHarness(self.store, ModelRegistry(CapabilityRegistry()))
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Create a scene and shot with one bounded Skill",
            proposals=(
                AgentPlanStepProposal(
                    step_id="setup",
                    skill_id=AgentSkillCatalog.SCENE_WITH_SHOT,
                    inputs={
                        "scene_id": "scene_trace_link",
                        "title": "Trace-linked scene",
                        "shot_id": "shot_trace_link",
                        "intent": "Trace-linked shot",
                    },
                ),
            ),
            plan_id="agent_plan_trace_link",
        )

        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="setup.scene",
        )
        current = coordinator.state(self.project.project_id, state.plan.plan_id)
        scene_task = current.tasks[0]
        self.assertEqual(scene_task.status, AgentTaskStatus.SUCCEEDED)
        trace = next(
            item
            for item in harness.traces.list(self.project.project_id)
            if item.trace_id == scene_task.trace_id
        )
        self.assertIn(state.plan.plan_id, trace.canonical_references)
        self.assertIn("setup.scene", trace.canonical_references)
        self.assertIn(AgentSkillCatalog.SCENE_WITH_SHOT, trace.canonical_references)
        self.assertIn("scene_trace_link", trace.canonical_references)

    def test_generation_submit_supplies_execution_only_null_authorization_by_default(self) -> None:
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_generation",
            title="Generation scene",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_generation",
            scene_id="scene_generation",
            intent="Generation target",
        )
        harness = AgentHarness(self.store, self._local_generation_registry())
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Submit one local generation job without persisting auth state",
            proposals=(
                AgentPlanStepProposal(
                    step_id="generate",
                    action_id="generation.submit",
                    inputs={
                        "shot_id": "shot_generation",
                        "model_id": "uv.image.stage16_runtime",
                        "inputs": {"prompt": "bounded local image"},
                        "contract": GenerationContract().to_dict(),
                        "idempotency_key": "stage16_runtime_default_auth",
                    },
                ),
            ),
            plan_id="agent_plan_default_auth",
        )

        result = coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="generate",
        )
        self.assertFalse(result.reused)
        self.assertEqual(len(harness.jobs.list(self.project.project_id)), 1)
        completed = coordinator.state(self.project.project_id, state.plan.plan_id)
        task = completed.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        trace = next(
            item
            for item in harness.traces.list(self.project.project_id)
            if item.trace_id == task.trace_id
        )
        self.assertIn(state.plan.plan_id, trace.canonical_references)
        self.assertIn("generate", trace.canonical_references)
        self.assertIn(result.job.job_id, trace.result_references.values())
        self.assertNotIn("authorization_token", state.plan.task("generate").inputs)


if __name__ == "__main__":
    unittest.main()
