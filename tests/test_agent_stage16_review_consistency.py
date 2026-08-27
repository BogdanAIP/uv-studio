from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStatus,
    AgentTaskStore,
    AgentTraceRecord,
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
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore


class _SuccessTraceFailure:
    def __init__(self, base: Any, *, action_id: str, error: BaseException) -> None:
        self._base = base
        self._action_id = action_id
        self._error = error

    def append(self, record: AgentTraceRecord):
        if record.status is AgentTraceStatus.SUCCEEDED and record.action_id == self._action_id:
            raise self._error
        return self._base.append(record)

    def list(self, project_id: str):
        return self._base.list(project_id)


class _PolicyLookupFailureCatalog:
    def __init__(self, base: Any) -> None:
        self._base = base

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def policy(self, *, project_id: str, action_id: str, model_id: str | None = None):
        raise RuntimeError("simulated execution policy lookup failure")


class _ChangingPolicyCatalog:
    """Return a different policy on a second base lookup to prove dispatch freezing."""

    def __init__(self, base: Any) -> None:
        self._base = base
        self.calls = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def policy(self, *, project_id: str, action_id: str, model_id: str | None = None):
        self.calls += 1
        policy = self._base.policy(
            project_id=project_id,
            action_id=action_id,
            model_id=model_id,
        )
        return replace(
            policy,
            effects=replace(policy.effects, reversible=(self.calls == 1)),
        )


class AgentStage16ReviewConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 review consistency",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_review_consistency",
        )
        production = ProductionSemanticService(self.store)
        production.create_scene(
            self.project.project_id,
            scene_id="scene_existing",
            title="Existing scene",
        )
        production.create_shot(
            self.project.project_id,
            shot_id="shot_existing",
            scene_id="scene_existing",
            intent="Existing shot",
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
            "Stage-16 review consistency capability.",
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
            "Local review-consistency transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage16_review_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage16_review_generator",
                title="Stage-16 review generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available for review-consistency proof.",
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
                    description="Named model for Stage-16 review consistency.",
                    capability_id="image.generate",
                    offer_id="stage16_review_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _generation_proposal(self, *, idempotency_key: str) -> AgentPlanStepProposal:
        return AgentPlanStepProposal(
            step_id="generate",
            action_id="generation.submit",
            inputs={
                "shot_id": "shot_existing",
                "model_id": "uv.image.stage16_review",
                "inputs": {"prompt": "review consistency"},
                "contract": GenerationContract().to_dict(),
                "idempotency_key": idempotency_key,
            },
            target_shot_id="shot_existing",
        )

    def test_policy_capture_failure_aborts_before_dispatch(self) -> None:
        planning = AgentTaskCoordinator(AgentHarness(self.store, self._empty_registry()))
        state = planning.create_plan(
            project_id=self.project.project_id,
            goal="Do not dispatch without durable execution policy",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_policy_failure_must_not_commit",
                        "title": "Must not commit",
                    },
                ),
            ),
            plan_id="agent_plan_policy_capture_failure",
        )

        execution_store = ProjectStore(self.projects_root)
        execution_harness = AgentHarness(execution_store, self._empty_registry())
        execution_harness.catalog = _PolicyLookupFailureCatalog(execution_harness.catalog)
        execution = AgentTaskCoordinator(execution_harness)
        with self.assertRaisesRegex(RuntimeError, "policy lookup failure"):
            execution.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        durable = execution.tasks.get(
            self.project.project_id,
            state.plan.plan_id,
            "scene",
        )
        self.assertEqual(durable.status, AgentTaskStatus.READY)
        scene_ids = {
            scene.scene_id
            for scene in ProductionSemanticService(execution_store)
            .state(self.project.project_id)
            .scenes
        }
        self.assertNotIn("scene_policy_failure_must_not_commit", scene_ids)
        self.assertEqual(execution_harness.traces.list(self.project.project_id), ())

    def test_injected_public_task_store_recovers_generation_context_from_evidence(self) -> None:
        registry = self._generation_registry()
        planning = AgentTaskCoordinator(AgentHarness(self.store, registry))
        state = planning.create_plan(
            project_id=self.project.project_id,
            goal="Recover context independently of injected task store",
            proposals=(self._generation_proposal(idempotency_key="idem_injected_store_context"),),
            plan_id="agent_plan_injected_store_context",
        )
        plan_context = state.plan.context_digest

        # Change canonical project context after planning, before execution.
        ProductionSemanticService(self.store).create_scene(
            self.project.project_id,
            scene_id="scene_after_planning",
            title="Context changed after planning",
        )

        execution_store = ProjectStore(self.projects_root)
        execution_harness = AgentHarness(execution_store, registry)
        execution_context = execution_harness.context.build(
            self.project.project_id,
            shot_id="shot_existing",
        ).digest
        self.assertNotEqual(execution_context, plan_context)
        execution_harness.traces = _SuccessTraceFailure(
            execution_harness.traces,
            action_id="generation.submit",
            error=SystemExit("simulated post-submit crash with injected task store"),
        )
        execution = AgentTaskCoordinator(
            execution_harness,
            task_store=AgentTaskStore(execution_store),
        )
        with self.assertRaises(SystemExit):
            execution.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="generate",
            )
        self.assertEqual(
            execution.tasks.get(
                self.project.project_id,
                state.plan.plan_id,
                "generate",
            ).status,
            AgentTaskStatus.RUNNING,
        )

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, registry)
        reopened = AgentTaskCoordinator(
            reopened_harness,
            task_store=AgentTaskStore(reopened_store),
        ).state(self.project.project_id, state.plan.plan_id)
        self.assertEqual(reopened.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        trace = reopened_harness.traces.list(self.project.project_id)[0]
        self.assertEqual(trace.context_digest, execution_context)
        self.assertNotEqual(trace.context_digest, plan_context)

    def test_execution_policy_is_frozen_to_the_persisted_dispatch_snapshot(self) -> None:
        registry = self._generation_registry()
        planning = AgentTaskCoordinator(AgentHarness(self.store, registry))
        state = planning.create_plan(
            project_id=self.project.project_id,
            goal="Use exactly the persisted execution policy for dispatch and recovery",
            proposals=(self._generation_proposal(idempotency_key="idem_policy_freeze"),),
            plan_id="agent_plan_policy_freeze",
        )

        execution_store = ProjectStore(self.projects_root)
        execution_harness = AgentHarness(execution_store, registry)
        changing = _ChangingPolicyCatalog(execution_harness.catalog)
        execution_harness.catalog = changing
        execution_harness.traces = _SuccessTraceFailure(
            execution_harness.traces,
            action_id="generation.submit",
            error=SystemExit("simulated post-submit policy freeze crash"),
        )
        execution = AgentTaskCoordinator(execution_harness)
        with self.assertRaises(SystemExit):
            execution.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="generate",
            )
        # The base catalog was consulted exactly once. AgentHarness consumed the bound
        # snapshot rather than performing a second, potentially different lookup.
        self.assertEqual(changing.calls, 1)

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, registry)
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        self.assertEqual(reopened.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        trace = reopened_harness.traces.list(self.project.project_id)[0]
        self.assertTrue(trace.policy.effects.reversible)

    def test_accept_take_recovery_preserves_affected_shot_identity(self) -> None:
        source = ProjectReference(
            id="source_accept_take_shot",
            kind="video",
            path="sources/accept-take-shot.mp4",
            metadata={"duration_us": 5_000_000},
        )
        source_path = (
            self.store.project_directory(self.project.project_id)
            / "sources"
            / "accept-take-shot.mp4"
        )
        source_path.write_bytes(b"stage16-affected-shot-recovery")
        current = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            sources=(*current.sources, source),
        )
        ProductionSemanticService(self.store).register_take(
            self.project.project_id,
            take_id="take_affected_shot",
            shot_id="shot_existing",
            reference_id=source.id,
        )

        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _SuccessTraceFailure(
            harness.traces,
            action_id="production.accept_take",
            error=SystemExit("simulated post-commit accept_take crash"),
        )
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Recover affected Shot provenance for accepted Take",
            proposals=(
                AgentPlanStepProposal(
                    step_id="accept",
                    action_id="production.accept_take",
                    inputs={
                        "take_id": "take_affected_shot",
                        "timeline_start_us": 0,
                        "duration_us": 1_000_000,
                    },
                ),
            ),
            plan_id="agent_plan_accept_take_affected_shot",
        )
        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="accept",
            )

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertIn("shot_existing", task.canonical_references)
        trace = reopened_harness.traces.list(self.project.project_id)[0]
        self.assertIn("shot_existing", trace.canonical_references)
        self.assertIn("take_affected_shot", trace.canonical_references)


if __name__ == "__main__":
    unittest.main()
