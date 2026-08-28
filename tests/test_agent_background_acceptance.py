from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from uv_studio.agent import (
    AgentBackgroundTaskCoordinator,
    AgentBackgroundWorker,
    AgentHarness,
    AgentPlanStepProposal,
    AgentSubagentCoordinator,
    AgentSubagentRequest,
    AgentSubagentRole,
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


class _MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 28, 7, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class _ScenePlanProposer:
    def __init__(self, scene_id: str) -> None:
        self.scene_id = scene_id

    def propose(self, context):
        return {
            "summary": "Create one scene through the Stage-17 bounded plan role.",
            "findings": [],
            "proposals": [
                {
                    "step_id": "scene",
                    "action_id": "production.create_scene",
                    "inputs": {
                        "scene_id": self.scene_id,
                        "title": "Background delegated scene",
                    },
                }
            ],
        }


class AgentBackgroundAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 18 background acceptance",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage18_background_acceptance",
        )
        self.clock = _MutableClock()

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
            "Local free capability for Stage-18 Job-history proof.",
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
            "stage18_background_generator",
            "Stage-18 background generator",
            "Local test transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage18_background_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage18_background_generator",
                title="Stage-18 background generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available for background Job proof.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage18_background",
                    title="UV Stage-18 Background Image",
                    description="Named model for background Job-history proof.",
                    capability_id="image.generate",
                    offer_id="stage18_background_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _worker(self, coordinator: AgentBackgroundTaskCoordinator, worker_id: str):
        return AgentBackgroundWorker(
            coordinator,
            worker_id=worker_id,
            lease_seconds=10,
            heartbeat_seconds=0,
        )

    def test_background_generation_preserves_exact_job_identity_on_reopen(self) -> None:
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_background_generation",
            title="Generation scene",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_background_generation",
            scene_id="scene_background_generation",
            intent="Generate one queued candidate",
        )

        registry = self._generation_registry()
        harness = AgentHarness(self.store, registry)
        coordinator = AgentBackgroundTaskCoordinator(harness, clock=self.clock)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Submit exactly one background generation Job",
            proposals=(
                AgentPlanStepProposal(
                    step_id="generate",
                    action_id="generation.submit",
                    inputs={
                        "shot_id": "shot_background_generation",
                        "model_id": "uv.image.stage18_background",
                        "inputs": {"prompt": "one exact background job"},
                        "contract": GenerationContract().to_dict(),
                        "idempotency_key": "idem_stage18_background_job",
                    },
                ),
            ),
            plan_id="agent_plan_background_generation",
        )
        self._worker(coordinator, "worker_generation").run_once(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
        )

        completed = coordinator.state(self.project.project_id, state.plan.plan_id)
        task = completed.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        job_id = task.result_references["job_id"]
        jobs = harness.generation.jobs.list(self.project.project_id)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, job_id)
        self.assertEqual(jobs[0].idempotency_key, "idem_stage18_background_job")
        self.assertEqual(jobs[0].attempts, ())

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, registry)
        reopened = AgentBackgroundTaskCoordinator(reopened_harness, clock=self.clock)
        reopened_state = reopened.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(reopened_state.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        reopened_jobs = reopened_harness.generation.jobs.list(self.project.project_id)
        self.assertEqual(len(reopened_jobs), 1)
        self.assertEqual(reopened_jobs[0].job_id, job_id)
        self.assertEqual(reopened_jobs[0].attempts, ())

        traces = [
            trace
            for trace in reopened_harness.traces.list(self.project.project_id)
            if trace.action_id == "generation.submit"
        ]
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].status, AgentTraceStatus.SUCCEEDED)
        self.assertEqual(traces[0].result_references["job_id"], job_id)

    def test_stage17_delegation_provenance_survives_background_execution_and_reopen(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        subagents = AgentSubagentCoordinator(
            harness,
            _ScenePlanProposer("scene_background_delegated"),
        )
        delegated = subagents.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create a delegated scene in background",
            )
        )
        state = subagents.persist_plan(
            delegated,
            plan_id="agent_plan_background_delegated",
        )
        self.assertIn(delegated.delegation_id, state.plan.canonical_references)

        coordinator = AgentBackgroundTaskCoordinator(harness, clock=self.clock)
        self._worker(coordinator, "worker_delegated").run_once(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
        )
        completed = coordinator.state(self.project.project_id, state.plan.plan_id)
        task = completed.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        trace = next(
            item
            for item in harness.traces.list(self.project.project_id)
            if item.trace_id == task.trace_id
        )
        self.assertIn(delegated.delegation_id, trace.canonical_references)

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentBackgroundTaskCoordinator(reopened_harness, clock=self.clock)
        reopened_task = reopened.state(self.project.project_id, state.plan.plan_id).tasks[0]
        reopened_trace = next(
            item
            for item in reopened_harness.traces.list(self.project.project_id)
            if item.trace_id == reopened_task.trace_id
        )
        self.assertIn(delegated.delegation_id, reopened_trace.canonical_references)
        self.assertTrue(
            any(
                reference.startswith("agent_delegate_bind_")
                for reference in reopened.state(
                    self.project.project_id,
                    state.plan.plan_id,
                ).plan.canonical_references
            )
        )

    def test_live_lease_keeps_running_task_inflight_until_expiry(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentBackgroundTaskCoordinator(harness, clock=self.clock)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Keep one legitimate claim in flight",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_live_background_lease",
                        "title": "Live lease",
                    },
                ),
            ),
            plan_id="agent_plan_live_background_lease",
        )
        worker = self._worker(coordinator, "worker_live_lease")
        worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )

        self.assertEqual(
            coordinator.state(self.project.project_id, state.plan.plan_id).tasks[0].status,
            AgentTaskStatus.RUNNING,
        )
        self.clock.advance(11)
        expired = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(expired.tasks[0].status, AgentTaskStatus.FAILED)
        lease = coordinator.leases.get(self.project.project_id, state.plan.plan_id, "scene")
        self.assertFalse(lease.active)
        self.assertEqual(lease.outcome, "recovered_failed")

    def test_failed_background_dependency_keeps_downstream_blocked(self) -> None:
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_runtime_duplicate",
            title="Already exists",
        )
        harness = AgentHarness(self.store, self._empty_registry())
        coordinator = AgentBackgroundTaskCoordinator(harness, clock=self.clock)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Prove failed dependency blocks background descendants",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_will_become_duplicate",
                        "title": "Will fail at runtime",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="shot",
                    action_id="production.create_shot",
                    inputs={
                        "shot_id": "shot_must_not_run_after_failure",
                        "scene_id": "scene_will_become_duplicate",
                        "intent": "Must remain blocked",
                    },
                    dependencies=("scene",),
                ),
            ),
            plan_id="agent_plan_background_dependency_failure",
        )
        # Change canonical state after planning so the first action fails through the
        # real Production authority rather than a synthetic worker exception.
        production.create_scene(
            self.project.project_id,
            scene_id="scene_will_become_duplicate",
            title="External canonical change",
        )

        worker = self._worker(coordinator, "worker_dependency_failure")
        claim = worker.claim(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        with self.assertRaises(Exception):
            worker.execute(claim)

        final = coordinator.state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(final.tasks[0].status, AgentTaskStatus.FAILED)
        # Preserve the merged Stage-16 state machine: failure does not rewrite a
        # dependent PLANNED task into CANCELLED, but it can never become runnable.
        self.assertEqual(final.tasks[1].status, AgentTaskStatus.PLANNED)
        self.assertEqual(coordinator.runnable(self.project.project_id, state.plan.plan_id), ())
        self.assertIsNone(
            worker.run_once(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
            )
        )
        current = ProductionSemanticService(self.store).state(self.project.project_id)
        with self.assertRaises(Exception):
            current.shot("shot_must_not_run_after_failure")


if __name__ == "__main__":
    unittest.main()
