from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStatus,
    AgentPlanStepProposal,
    AgentPlanningError,
    AgentPortableStateError,
    AgentSkillCatalog,
    AgentSkillError,
    AgentTaskBlocked,
    AgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
)
from uv_studio.capabilities.authorization import ExecutionConsentRequired
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
from uv_studio.production.semantics import ProductionSemanticError
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Agent planning",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_agent_planning",
        )
        self.production = ProductionSemanticService(self.store)
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_existing",
            title="Existing scene",
        )
        self.production.create_shot(
            self.project.project_id,
            shot_id="shot_existing",
            scene_id="scene_existing",
            intent="Existing generation target",
        )
        self.registry = ModelRegistry(CapabilityRegistry())
        self.harness = AgentHarness(self.store, self.registry)
        self.coordinator = AgentTaskCoordinator(self.harness)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _generation_registry(
        *,
        locality: LocalityClass,
        cost: CostClass,
        availability: OfferAvailability = OfferAvailability.AVAILABLE,
    ) -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Stage-16 planning test capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
            effects=CapabilityEffects(
                mutates_project=True,
                generates_media=True,
                long_running=True,
                reversible=False,
                cost_bearing=cost is not CostClass.FREE,
            ),
        )
        adapter = AdapterDefinition(
            "planning_test_generator",
            "Planning test generator",
            "Bounded Stage-16 test transport.",
            AdapterKind.LOCAL if locality is LocalityClass.LOCAL else AdapterKind.RUNTIME,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="planning_test_generator.image_generate",
                capability_id="image.generate",
                adapter_id="planning_test_generator",
                title="Planning test image generator",
                availability=availability,
                reason=(
                    "Available for Stage-16 planning tests."
                    if availability is OfferAvailability.AVAILABLE
                    else "Provider configuration is required."
                ),
                locality=locality,
                cost_class=cost,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.planning_test",
                    title="UV Planning Test Image",
                    description="Named model used only by Stage-16 tests.",
                    capability_id="image.generate",
                    offer_id="planning_test_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    @staticmethod
    def _generation_inputs(idempotency_key: str) -> dict[str, object]:
        return {
            "shot_id": "shot_existing",
            "model_id": "uv.image.planning_test",
            "inputs": {"prompt": "bounded portrait"},
            "contract": GenerationContract().to_dict(),
            "idempotency_key": idempotency_key,
        }

    def test_skill_plan_executes_dependency_chain_and_reopens(self) -> None:
        state = self.coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Create one scene and its first shot",
            proposals=(
                AgentPlanStepProposal(
                    step_id="setup",
                    skill_id=AgentSkillCatalog.SCENE_WITH_SHOT,
                    inputs={
                        "scene_id": "scene_skill",
                        "title": "Skill scene",
                        "summary": "Created through a bounded Skill",
                        "shot_id": "shot_skill",
                        "intent": "First bounded shot",
                    },
                ),
            ),
            plan_id="agent_plan_skill_proof",
        )

        self.assertEqual(state.status, AgentPlanStatus.ACTIVE)
        self.assertEqual(
            tuple(task.task_id for task in state.tasks),
            ("setup.scene", "setup.shot"),
        )
        self.assertEqual(state.tasks[0].status, AgentTaskStatus.READY)
        self.assertEqual(state.tasks[1].status, AgentTaskStatus.PLANNED)
        self.assertEqual(
            state.plan.task("setup.shot").dependencies,
            ("setup.scene",),
        )
        self.assertTrue(
            state.plan.task("setup.scene").policy.effects.mutates_project
        )

        with self.assertRaises(AgentTaskBlocked):
            self.coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="setup.shot",
            )

        scene_result = self.coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="setup.scene",
        )
        self.assertTrue(scene_result.transaction_id.startswith("tx_"))
        after_scene = self.coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(after_scene.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        self.assertEqual(after_scene.tasks[1].status, AgentTaskStatus.READY)
        self.assertIsNotNone(after_scene.tasks[0].trace_id)
        self.assertEqual(
            after_scene.tasks[0].skill_id,
            AgentSkillCatalog.SCENE_WITH_SHOT,
        )
        self.assertIn("scene_skill", after_scene.tasks[0].canonical_references)

        shot_result = self.coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="setup.shot",
        )
        self.assertTrue(shot_result.transaction_id.startswith("tx_"))
        completed = self.coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(completed.status, AgentPlanStatus.SUCCEEDED)
        self.assertTrue(all(task.status is AgentTaskStatus.SUCCEEDED for task in completed.tasks))
        self.assertIn("shot_skill", completed.tasks[1].canonical_references)
        shared = self.production.state(self.project.project_id)
        self.assertEqual(shared.shot("shot_skill").scene_id, "scene_skill")

        trace_ids = {trace.trace_id for trace in self.harness.traces.list(self.project.project_id)}
        self.assertTrue(all(task.trace_id in trace_ids for task in completed.tasks))

        reopened_store = ProjectStore(self.store.root)
        reopened_harness = AgentHarness(
            reopened_store,
            ModelRegistry(CapabilityRegistry()),
        )
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        self.assertEqual(reopened.status, AgentPlanStatus.SUCCEEDED)
        self.assertEqual(
            tuple(task.trace_id for task in reopened.tasks),
            tuple(task.trace_id for task in completed.tasks),
        )

    def test_planner_rejects_cycles_missing_dependencies_and_unknown_authority(self) -> None:
        with self.assertRaisesRegex(AgentPlanningError, "cycle"):
            self.coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Cyclic plan",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="a",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_a", "title": "A"},
                        dependencies=("b",),
                    ),
                    AgentPlanStepProposal(
                        step_id="b",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_b", "title": "B"},
                        dependencies=("a",),
                    ),
                ),
            )

        with self.assertRaisesRegex(AgentPlanningError, "missing dependencies"):
            self.coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Missing dependency",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="a",
                        action_id="production.create_scene",
                        inputs={"scene_id": "scene_missing_dep", "title": "Missing"},
                        dependencies=("unknown",),
                    ),
                ),
            )

        with self.assertRaisesRegex(AgentPlanningError, "unknown Agent action"):
            self.coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Forbidden direct file write",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="write",
                        action_id="project.write_file",
                        inputs={"relative_path": "notes/pwned.txt", "content": "blocked"},
                    ),
                ),
            )
        self.assertFalse(
            (self.store.project_directory(self.project.project_id) / "notes" / "pwned.txt").exists()
        )

        with self.assertRaises(AgentSkillError):
            self.coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Unknown skill",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="skill",
                        skill_id="unknown.skill",
                        inputs={},
                    ),
                ),
            )

    def test_plan_and_skill_state_reject_secrets_host_paths_and_invalid_transition(self) -> None:
        with self.assertRaises(AgentPortableStateError):
            AgentPlanStepProposal(
                step_id="secret",
                action_id="production.create_scene",
                inputs={"authorization_token": "secret-token"},
            )
        with self.assertRaises(AgentPortableStateError):
            AgentPlanStepProposal(
                step_id="path",
                action_id="production.create_scene",
                inputs={"scene_id": "scene_path", "title": r"C:\Users\agent\secret.txt"},
            )

        skill = self.coordinator.planner.skills.describe(
            AgentSkillCatalog.SCENE_WITH_SHOT
        )
        self.assertEqual(
            skill["action_ids"],
            ["production.create_scene", "production.create_shot"],
        )
        self.assertTrue(skill["effects"]["mutates_project"])
        self.assertFalse(skill["uses_job_manager"])
        self.assertFalse(skill["authorization_may_be_required"])
        self.assertTrue(
            all(
                authority.startswith("uv_studio.production.commands.")
                for authority in skill["authorities"]
            )
        )

        state = self.coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Transition proof",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_transition", "title": "Transition"},
                ),
            ),
            plan_id="agent_plan_transition_proof",
        )
        ready = state.tasks[0]
        with self.assertRaisesRegex(AgentTaskStateError, "invalid Agent Task transition"):
            self.coordinator.tasks.transition(ready, AgentTaskStatus.SUCCEEDED)

    def test_failed_task_is_durable_and_does_not_unlock_or_report_success(self) -> None:
        state = self.coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Fail first task and keep dependent blocked",
            proposals=(
                AgentPlanStepProposal(
                    step_id="bad_shot",
                    action_id="production.create_shot",
                    inputs={
                        "shot_id": "shot_bad",
                        "scene_id": "scene_does_not_exist",
                        "intent": "Must fail",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="after",
                    action_id="production.create_scene",
                    inputs={"scene_id": "scene_after", "title": "Must remain blocked"},
                    dependencies=("bad_shot",),
                ),
            ),
            plan_id="agent_plan_failure_proof",
        )

        with self.assertRaises(ProductionSemanticError):
            self.coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="bad_shot",
            )
        failed = self.coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(failed.status, AgentPlanStatus.FAILED)
        by_id = {task.task_id: task for task in failed.tasks}
        self.assertEqual(by_id["bad_shot"].status, AgentTaskStatus.FAILED)
        self.assertIsNotNone(by_id["bad_shot"].trace_id)
        self.assertEqual(by_id["after"].status, AgentTaskStatus.PLANNED)
        self.assertFalse(
            any(scene.scene_id == "scene_after" for scene in self.production.state(self.project.project_id).scenes)
        )
        with self.assertRaises(AgentTaskStateError):
            self.coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="bad_shot",
            )

    def test_unavailable_generation_is_rejected_at_planning_time(self) -> None:
        registry = self._generation_registry(
            locality=LocalityClass.REMOTE,
            cost=CostClass.POTENTIALLY_PAID,
            availability=OfferAvailability.CONFIGURATION_REQUIRED,
        )
        coordinator = AgentTaskCoordinator(AgentHarness(self.store, registry))
        with self.assertRaisesRegex(AgentPlanningError, "unavailable"):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Unavailable generation must stay unavailable",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="generate",
                        action_id="generation.submit",
                        inputs=self._generation_inputs("idem_unavailable_planning"),
                    ),
                ),
            )
        self.assertEqual(coordinator.harness.jobs.list(self.project.project_id), ())

    def test_d017_failure_and_succeeded_task_replay_do_not_duplicate_generation_jobs(self) -> None:
        remote_registry = self._generation_registry(
            locality=LocalityClass.REMOTE,
            cost=CostClass.POTENTIALLY_PAID,
        )
        remote = AgentTaskCoordinator(AgentHarness(self.store, remote_registry))
        remote_state = remote.create_plan(
            project_id=self.project.project_id,
            goal="Remote generation requires exact D-017 authorization",
            proposals=(
                AgentPlanStepProposal(
                    step_id="remote_generate",
                    action_id="generation.submit",
                    inputs=self._generation_inputs("idem_remote_task"),
                ),
            ),
            plan_id="agent_plan_remote_d017",
        )
        self.assertTrue(remote_state.plan.task("remote_generate").policy.authorization_required)
        with self.assertRaises(ExecutionConsentRequired):
            remote.execute_task(
                project_id=self.project.project_id,
                plan_id=remote_state.plan.plan_id,
                task_id="remote_generate",
                runtime_inputs={"authorization_token": None},
            )
        remote_failed = remote.state(self.project.project_id, remote_state.plan.plan_id)
        self.assertEqual(remote_failed.status, AgentPlanStatus.FAILED)
        self.assertEqual(remote.harness.jobs.list(self.project.project_id), ())
        self.assertNotIn(
            "authorization_token",
            json.dumps(remote_failed.to_dict(), ensure_ascii=False),
        )

        local_registry = self._generation_registry(
            locality=LocalityClass.LOCAL,
            cost=CostClass.FREE,
        )
        local = AgentTaskCoordinator(AgentHarness(self.store, local_registry))
        local_state = local.create_plan(
            project_id=self.project.project_id,
            goal="Create exactly one durable generation Job",
            proposals=(
                AgentPlanStepProposal(
                    step_id="local_generate",
                    action_id="generation.submit",
                    inputs=self._generation_inputs("idem_local_task"),
                ),
            ),
            plan_id="agent_plan_local_job",
        )
        result = local.execute_task(
            project_id=self.project.project_id,
            plan_id=local_state.plan.plan_id,
            task_id="local_generate",
            runtime_inputs={"authorization_token": None},
        )
        self.assertFalse(result.reused)
        self.assertEqual(len(local.harness.jobs.list(self.project.project_id)), 1)
        completed = local.state(self.project.project_id, local_state.plan.plan_id)
        self.assertEqual(completed.status, AgentPlanStatus.SUCCEEDED)
        self.assertEqual(
            completed.tasks[0].result_references["job_id"],
            result.job.job_id,
        )
        with self.assertRaises(AgentTaskStateError):
            local.execute_task(
                project_id=self.project.project_id,
                plan_id=local_state.plan.plan_id,
                task_id="local_generate",
                runtime_inputs={"authorization_token": None},
            )
        self.assertEqual(len(local.harness.jobs.list(self.project.project_id)), 1)


if __name__ == "__main__":
    unittest.main()
