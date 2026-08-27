from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStatus,
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
from uv_studio.projects.timeline import TimelineStore


class _SuccessTraceFailure:
    def __init__(
        self,
        base: Any,
        *,
        action_id: str,
        error: BaseException,
    ) -> None:
        self._base = base
        self._action_id = action_id
        self._error = error

    def append(self, record: AgentTraceRecord):
        if (
            record.status is AgentTraceStatus.SUCCEEDED
            and record.action_id == self._action_id
        ):
            raise self._error
        return self._base.append(record)

    def list(self, project_id: str):
        return self._base.list(project_id)


class AgentStage16FinalReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 final review",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_final_review",
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
    def _generation_registry(*, reversible: bool) -> ModelRegistry:
        capability = CapabilityDefinition(
            "image.generate",
            "Image generation",
            "Stage-16 execution-policy recovery capability.",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.IMAGE,),
            asynchronous=True,
            effects=CapabilityEffects(
                mutates_project=True,
                generates_media=True,
                long_running=True,
                reversible=reversible,
            ),
        )
        adapter = AdapterDefinition(
            "stage16_policy_generator",
            "Stage-16 policy generator",
            "Local test transport.",
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
                reason="Available for execution-policy recovery.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.stage16_policy",
                    title="UV Stage-16 Policy Image",
                    description="Named model for execution-policy recovery proof.",
                    capability_id="image.generate",
                    offer_id="stage16_policy_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _register_video_take(self) -> tuple[ProjectReference, str]:
        source = ProjectReference(
            id="source_accept_take_video",
            kind="video",
            path="sources/accept-take.mp4",
            metadata={"duration_us": 5_000_000},
        )
        source_path = (
            self.store.project_directory(self.project.project_id)
            / "sources"
            / "accept-take.mp4"
        )
        source_path.write_bytes(b"stage16-accept-take-recovery")
        current = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            sources=(*current.sources, source),
        )
        take_id = "take_accept_recovery"
        ProductionSemanticService(self.store).register_take(
            self.project.project_id,
            take_id=take_id,
            shot_id="shot_existing",
            reference_id=source.id,
        )
        return source, take_id

    def test_trace_write_oserror_leaves_committed_task_recoverable(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _SuccessTraceFailure(
            harness.traces,
            action_id="production.create_scene",
            error=OSError("simulated success trace persistence failure"),
        )
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Commit once and recover after trace I/O failure",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_trace_io_recovery",
                        "title": "Committed despite trace I/O failure",
                    },
                ),
            ),
            plan_id="agent_plan_trace_io_recovery",
        )

        with self.assertRaisesRegex(OSError, "trace persistence"):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        durable = coordinator.tasks.get(
            self.project.project_id,
            state.plan.plan_id,
            "scene",
        )
        self.assertEqual(durable.status, AgentTaskStatus.RUNNING)
        self.assertEqual(
            ProductionSemanticService(self.store)
            .state(self.project.project_id)
            .scene("scene_trace_io_recovery")
            .title,
            "Committed despite trace I/O failure",
        )

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertIn("transaction_id", task.result_references)
        self.assertEqual(len(reopened_harness.traces.list(self.project.project_id)), 1)

    def test_accept_take_recovery_restores_generated_track_and_clip_ids(self) -> None:
        _, take_id = self._register_video_take()
        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _SuccessTraceFailure(
            harness.traces,
            action_id="production.accept_take",
            error=SystemExit("simulated post-commit accept_take crash"),
        )
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Accept a Take and recover generated Timeline identities",
            proposals=(
                AgentPlanStepProposal(
                    step_id="accept",
                    action_id="production.accept_take",
                    inputs={
                        "take_id": take_id,
                        "timeline_start_us": 0,
                        "duration_us": 1_000_000,
                    },
                ),
            ),
            plan_id="agent_plan_accept_take_ids",
        )

        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="accept",
            )

        timeline = TimelineStore(self.store).load(self.project.project_id)
        track = timeline.track("production_video")
        self.assertEqual(len(track.clips), 1)
        generated_clip_id = track.clips[0].clip_id
        self.assertTrue(generated_clip_id.startswith("clip_"))

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertEqual(task.result_references["track_id"], "production_video")
        self.assertEqual(task.result_references["clip_id"], generated_clip_id)
        trace = reopened_harness.traces.list(self.project.project_id)[0]
        self.assertEqual(trace.result_references["track_id"], "production_video")
        self.assertEqual(trace.result_references["clip_id"], generated_clip_id)

    def test_recovered_trace_uses_durable_execution_time_policy(self) -> None:
        planning_registry = self._generation_registry(reversible=False)
        planning = AgentTaskCoordinator(AgentHarness(self.store, planning_registry))
        state = planning.create_plan(
            project_id=self.project.project_id,
            goal="Recover the policy that was actually used for generation dispatch",
            proposals=(
                AgentPlanStepProposal(
                    step_id="generate",
                    action_id="generation.submit",
                    inputs={
                        "shot_id": "shot_existing",
                        "model_id": "uv.image.stage16_policy",
                        "inputs": {"prompt": "execution-time policy"},
                        "contract": GenerationContract().to_dict(),
                        "idempotency_key": "idem_stage16_execution_policy",
                    },
                    target_shot_id="shot_existing",
                ),
            ),
            plan_id="agent_plan_execution_policy",
        )
        self.assertFalse(state.plan.task("generate").policy.effects.reversible)

        execution_store = ProjectStore(self.projects_root)
        execution_harness = AgentHarness(
            execution_store,
            self._generation_registry(reversible=True),
        )
        execution_harness.traces = _SuccessTraceFailure(
            execution_harness.traces,
            action_id="generation.submit",
            error=SystemExit("simulated post-submit policy recovery crash"),
        )
        execution = AgentTaskCoordinator(execution_harness)
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
        reopened_harness = AgentHarness(reopened_store, planning_registry)
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        trace = reopened_harness.traces.list(self.project.project_id)[0]
        self.assertTrue(trace.policy.effects.reversible)
        self.assertFalse(reopened.plan.task("generate").policy.effects.reversible)
        self.assertEqual(trace.policy.model_id, "uv.image.stage16_policy")


if __name__ == "__main__":
    unittest.main()
