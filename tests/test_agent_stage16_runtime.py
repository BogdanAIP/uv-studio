from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AGENT_SKILL_SCHEMA_VERSION,
    AgentHarness,
    AgentPlanStatus,
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
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 runtime",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_runtime",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _empty_registry() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

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

    def _scene_plan(
        self,
        coordinator: AgentTaskCoordinator,
        *,
        plan_id: str,
        step_id: str = "scene",
        scene_id: str = "scene_runtime",
    ):
        return coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Create one bounded scene",
            proposals=(
                AgentPlanStepProposal(
                    step_id=step_id,
                    action_id="production.create_scene",
                    inputs={"scene_id": scene_id, "title": scene_id},
                ),
            ),
            plan_id=plan_id,
        )

    def test_skill_catalog_exposes_stable_schema_metadata(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        catalog = AgentSkillCatalog(harness.catalog)
        description = catalog.describe(AgentSkillCatalog.SCENE_WITH_SHOT)
        self.assertEqual(description["schema_version"], AGENT_SKILL_SCHEMA_VERSION)
        self.assertEqual(description["skill_id"], AgentSkillCatalog.SCENE_WITH_SHOT)
        self.assertEqual(
            description["action_ids"],
            ["production.create_scene", "production.create_shot"],
        )
        self.assertFalse(description["uses_job_manager"])
        self.assertFalse(description["authorization_may_be_required"])

    def test_custom_plan_id_is_discovered_by_plan_store_list(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentTaskCoordinator(harness)
        state = self._scene_plan(
            coordinator,
            plan_id="custom_plan",
            scene_id="scene_custom_plan",
        )

        plan_ids = tuple(
            plan.plan_id for plan in coordinator.plans.list(self.project.project_id)
        )
        self.assertIn(state.plan.plan_id, plan_ids)
        self.assertIn("custom_plan", plan_ids)

    def test_reopen_repairs_partial_initial_task_set_without_reset(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentTaskCoordinator(harness)
        plan = coordinator.planner.build(
            project_id=self.project.project_id,
            goal="Recover an interrupted plan/task initialization",
            proposals=(
                AgentPlanStepProposal(
                    step_id="setup",
                    skill_id=AgentSkillCatalog.SCENE_WITH_SHOT,
                    inputs={
                        "scene_id": "scene_partial_init",
                        "title": "Partial initialization",
                        "shot_id": "shot_partial_init",
                        "intent": "Recovered dependent shot",
                    },
                ),
            ),
            plan_id="custom_partial_plan",
        )
        coordinator.plans.append(plan)
        records = coordinator.tasks.initialize(plan)
        first_before = records[0]
        missing = records[1]
        coordinator.tasks.records.path(
            self.project.project_id,
            missing.record_id,
        ).unlink()

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness)
        recovered = reopened.state(self.project.project_id, plan.plan_id)

        self.assertEqual(len(recovered.tasks), 2)
        self.assertEqual(recovered.tasks[0].task_id, "setup.scene")
        self.assertEqual(recovered.tasks[0].record_id, first_before.record_id)
        self.assertEqual(recovered.tasks[0].status, AgentTaskStatus.READY)
        self.assertEqual(recovered.tasks[1].task_id, "setup.shot")
        self.assertEqual(recovered.tasks[1].status, AgentTaskStatus.PLANNED)
        self.assertIn(
            plan.plan_id,
            tuple(item.plan_id for item in reopened.plans.list(self.project.project_id)),
        )

    def test_skill_execution_correlates_plan_task_and_skill_in_stage15_trace(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
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
        inspection = current.to_dict()
        self.assertEqual(inspection["status"], AgentPlanStatus.ACTIVE.value)
        self.assertEqual(inspection["created_at"], current.plan.created_at)
        self.assertEqual(inspection["updated_at"], current.updated_at)

    def test_reopen_fails_abandoned_running_task_without_replay(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentTaskCoordinator(harness)
        state = self._scene_plan(
            coordinator,
            plan_id="agent_plan_interrupted",
            scene_id="scene_interrupted",
        )
        ready = state.tasks[0]
        coordinator.tasks.transition(ready, AgentTaskStatus.RUNNING)

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness)
        recovered = reopened.state(self.project.project_id, state.plan.plan_id)
        task = recovered.tasks[0]

        self.assertEqual(task.status, AgentTaskStatus.FAILED)
        self.assertEqual(recovered.status, AgentPlanStatus.FAILED)
        self.assertIsNone(task.trace_id)
        self.assertIn("interrupted", task.error_message.lower())
        self.assertEqual(len(reopened_harness.traces.list(self.project.project_id)), 0)
        self.assertEqual(
            len(ProductionSemanticService(reopened_store).state(self.project.project_id).scenes),
            0,
        )

    def test_mixed_succeeded_and_cancelled_tasks_make_terminal_plan(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Finish with one success and one explicit cancellation",
            proposals=(
                AgentPlanStepProposal(
                    step_id="keep",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_keep", "title": "Keep"},
                ),
                AgentPlanStepProposal(
                    step_id="skip",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_skip", "title": "Skip"},
                ),
            ),
            plan_id="agent_plan_mixed_terminal",
        )
        coordinator.cancel_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="skip",
        )
        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="keep",
        )
        completed = coordinator.state(self.project.project_id, state.plan.plan_id)
        statuses = {task.task_id: task.status for task in completed.tasks}
        self.assertEqual(statuses["keep"], AgentTaskStatus.SUCCEEDED)
        self.assertEqual(statuses["skip"], AgentTaskStatus.CANCELLED)
        self.assertEqual(completed.status, AgentPlanStatus.CANCELLED)
        self.assertEqual(coordinator.runnable(self.project.project_id, state.plan.plan_id), ())

    def test_cancelling_dependency_cancels_planned_descendants(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Cancel an impossible dependent chain",
            proposals=(
                AgentPlanStepProposal(
                    step_id="setup",
                    skill_id=AgentSkillCatalog.SCENE_WITH_SHOT,
                    inputs={
                        "scene_id": "scene_cancel_chain",
                        "title": "Cancel chain",
                        "shot_id": "shot_cancel_chain",
                        "intent": "Must never run",
                    },
                ),
            ),
            plan_id="agent_plan_cancel_chain",
        )
        coordinator.cancel_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="setup.scene",
        )
        completed = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(
            tuple(task.status for task in completed.tasks),
            (AgentTaskStatus.CANCELLED, AgentTaskStatus.CANCELLED),
        )
        self.assertEqual(completed.status, AgentPlanStatus.CANCELLED)
        self.assertEqual(coordinator.runnable(self.project.project_id, state.plan.plan_id), ())

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
        self.assertEqual(completed.status, AgentPlanStatus.SUCCEEDED)
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
