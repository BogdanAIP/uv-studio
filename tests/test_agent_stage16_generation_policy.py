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
    AgentTaskStateError,
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


class _OfferMutationAfterPolicyCatalog:
    """Mutate one offer only after the old Agent policy has been returned."""

    def __init__(self, base: Any, capabilities: CapabilityRegistry, offer_id: str) -> None:
        self._base = base
        self._capabilities = capabilities
        self._offer_id = offer_id
        self.mutated = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def policy(self, *, project_id: str, action_id: str, model_id: str | None = None):
        policy = self._base.policy(
            project_id=project_id,
            action_id=action_id,
            model_id=model_id,
        )
        if action_id == "generation.submit" and not self.mutated:
            current = self._capabilities.get_offer(self._offer_id)
            self._capabilities.upsert_offer(replace(current, asynchronous=True))
            self.mutated = True
        return policy


class AgentStage16GenerationPolicyBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 generation policy binding",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_generation_policy_binding",
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
    def _generation_registry() -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Stage-16 generation policy binding capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=False,
            effects=CapabilityEffects(
                mutates_project=True,
                generates_media=True,
                long_running=False,
                reversible=False,
            ),
        )
        adapter = AdapterDefinition(
            "stage16_policy_generator",
            "Stage-16 policy generator",
            "Local generation preparation consistency transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="stage16_policy_generator.image_generate",
                capability_id="image.generate",
                adapter_id="stage16_policy_generator",
                title="Stage-16 policy generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available for generation policy binding proof.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=False,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage16_policy",
                    title="UV Stage-16 Policy Image",
                    description="Named model for generation policy binding.",
                    capability_id="image.generate",
                    offer_id="stage16_policy_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    @staticmethod
    def _proposal() -> AgentPlanStepProposal:
        return AgentPlanStepProposal(
            step_id="generate",
            action_id="generation.submit",
            inputs={
                "shot_id": "shot_existing",
                "model_id": "uv.image.stage16_policy",
                "inputs": {"prompt": "bind preparation"},
                "contract": GenerationContract().to_dict(),
                "idempotency_key": "idem_generation_policy_binding",
            },
            target_shot_id="shot_existing",
        )

    def test_offer_change_after_policy_lookup_is_rejected_before_job_commit(self) -> None:
        registry = self._generation_registry()
        planning = AgentTaskCoordinator(AgentHarness(self.store, registry))
        state = planning.create_plan(
            project_id=self.project.project_id,
            goal="Bind generation preparation to frozen policy",
            proposals=(self._proposal(),),
            plan_id="agent_plan_generation_policy_binding",
        )

        execution_store = ProjectStore(self.projects_root)
        execution_harness = AgentHarness(execution_store, registry)
        capabilities = registry.capability_registry
        execution_harness.catalog = _OfferMutationAfterPolicyCatalog(
            execution_harness.catalog,
            capabilities,
            "stage16_policy_generator.image_generate",
        )
        execution = AgentTaskCoordinator(execution_harness)

        with self.assertRaisesRegex(
            AgentTaskStateError,
            "generation preparation no longer matches",
        ):
            execution.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="generate",
            )

        # The registry changed only after the old policy snapshot was returned.
        self.assertTrue(
            capabilities.effects_for_offer(
                "stage16_policy_generator.image_generate"
            ).long_running
        )
        # The mismatch is rejected before D-017 consumption / durable Job creation.
        self.assertEqual(execution_harness.jobs.list(self.project.project_id), ())
        task = execution.tasks.get(
            self.project.project_id,
            state.plan.plan_id,
            "generate",
        )
        self.assertEqual(task.status, AgentTaskStatus.FAILED)
        traces = execution_harness.traces.list(self.project.project_id)
        self.assertEqual(len(traces), 1)
        self.assertFalse(traces[0].policy.effects.long_running)


if __name__ == "__main__":
    unittest.main()
