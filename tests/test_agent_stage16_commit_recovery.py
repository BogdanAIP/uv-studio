from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentPlanningError,
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
from uv_studio.editor.timeline_commands import CreateTrackCommand, TimelineCommandService
from uv_studio.generation.models import GenerationContract, ModelDefinition, ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.store import ProjectStore
from uv_studio.projects.timeline import TimelineStore


class _CrashOnSuccessTraceStore:
    """Simulate process loss after canonical success but before trace persistence."""

    def __init__(self, base: Any, *, crash_action_id: str | None = None) -> None:
        self._base = base
        self._crash_action_id = crash_action_id

    def append(self, record: AgentTraceRecord):
        should_crash = (
            record.status is AgentTraceStatus.SUCCEEDED
            and (
                self._crash_action_id is None
                or record.action_id == self._crash_action_id
            )
        )
        if should_crash:
            raise SystemExit("simulated post-commit/pre-trace process loss")
        return self._base.append(record)

    def list(self, project_id: str):
        return self._base.list(project_id)


class AgentStage16CommitRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 16 committed-effect recovery",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage16_commit_recovery",
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
            intent="Generation target",
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
            "Stage-16 committed-effect recovery capability.",
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
            "commit_recovery_generator",
            "Commit recovery generator",
            "Local Stage-16 recovery test transport.",
            AdapterKind.LOCAL,
        )
        capabilities = CapabilityRegistry((capability,), (adapter,))
        capabilities.register_offer(
            CapabilityOffer(
                offer_id="commit_recovery_generator.image_generate",
                capability_id="image.generate",
                adapter_id="commit_recovery_generator",
                title="Commit recovery image generator",
                availability=OfferAvailability.AVAILABLE,
                reason="Available for Stage-16 recovery tests.",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=True,
            )
        )
        return ModelRegistry(
            capabilities,
            (
                ModelDefinition(
                    model_id="uv.image.commit_recovery",
                    title="UV Commit Recovery Image",
                    description="Named model used only by Stage-16 recovery tests.",
                    capability_id="image.generate",
                    offer_id="commit_recovery_generator.image_generate",
                    output_kind=MediaKind.IMAGE,
                ),
            ),
        )

    def _register_video_source(self) -> ProjectReference:
        source = ProjectReference(
            id="source_recovery_video",
            kind="video",
            path="sources/recovery-video.mp4",
            metadata={"duration_us": 10_000_000},
        )
        source_path = (
            self.store.project_directory(self.project.project_id)
            / "sources"
            / "recovery-video.mp4"
        )
        source_path.write_bytes(b"stage16-timeline-recovery")
        current = self.store.load_project(self.project.project_id)
        self.store.update_project(
            self.project.project_id,
            sources=(*current.sources, source),
        )
        return source

    def test_planner_rejects_missing_required_action_inputs_before_persistence(self) -> None:
        coordinator = AgentTaskCoordinator(
            AgentHarness(self.store, self._empty_registry())
        )
        with self.assertRaisesRegex(
            AgentPlanningError,
            "production.create_scene.*missing required inputs",
        ):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Reject an incomplete scene command",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={},
                    ),
                ),
                plan_id="agent_plan_missing_required_inputs",
            )
        self.assertEqual(
            tuple(
                plan.plan_id
                for plan in coordinator.plans.list(self.project.project_id)
                if plan.plan_id == "agent_plan_missing_required_inputs"
            ),
            (),
        )

    def test_planner_rejects_invalid_non_generation_types_before_persistence(self) -> None:
        coordinator = AgentTaskCoordinator(
            AgentHarness(self.store, self._empty_registry())
        )
        with self.assertRaisesRegex(
            AgentPlanningError,
            "production.create_scene.*inputs are invalid",
        ):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Reject deterministic type errors before durable planning",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="scene",
                        action_id="production.create_scene",
                        inputs={"scene_id": 7, "title": []},
                    ),
                ),
                plan_id="agent_plan_invalid_scene_types",
            )
        self.assertNotIn(
            "agent_plan_invalid_scene_types",
            {plan.plan_id for plan in coordinator.plans.list(self.project.project_id)},
        )

        with self.assertRaisesRegex(
            AgentPlanningError,
            "timeline.move_clip.*inputs are invalid",
        ):
            coordinator.create_plan(
                project_id=self.project.project_id,
                goal="Reject invalid timeline time type",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="move",
                        action_id="timeline.move_clip",
                        inputs={"clip_id": "clip_known", "timeline_start_us": True},
                    ),
                ),
                plan_id="agent_plan_invalid_timeline_types",
            )
        self.assertNotIn(
            "agent_plan_invalid_timeline_types",
            {plan.plan_id for plan in coordinator.plans.list(self.project.project_id)},
        )

    def test_reopen_recovers_committed_production_mutation_without_replay(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _CrashOnSuccessTraceStore(harness.traces)
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Create one scene and survive trace-loss crash",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_post_commit_crash",
                        "title": "Committed before trace",
                    },
                ),
            ),
            plan_id="agent_plan_post_commit_crash",
        )

        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        durable_running = coordinator.tasks.get(
            self.project.project_id,
            state.plan.plan_id,
            "scene",
        )
        self.assertEqual(durable_running.status, AgentTaskStatus.RUNNING)
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(
            production.scene("scene_post_commit_crash").title,
            "Committed before trace",
        )
        self.assertEqual(harness.traces.list(self.project.project_id), ())

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertIsNotNone(task.trace_id)
        self.assertTrue(task.result_references["transaction_id"].startswith("tx_"))
        traces = reopened_harness.traces.list(self.project.project_id)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].trace_id, task.trace_id)
        self.assertEqual(
            traces[0].result_references["transaction_id"],
            task.result_references["transaction_id"],
        )
        # Reopen recovery proves the already committed mutation. It must not replay it.
        production_after = ProductionSemanticService(reopened_store).state(
            self.project.project_id
        )
        self.assertEqual(
            len(
                [
                    scene
                    for scene in production_after.scenes
                    if scene.scene_id == "scene_post_commit_crash"
                ]
            ),
            1,
        )

    def test_recovered_trace_uses_execution_time_context_after_dependency_change(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _CrashOnSuccessTraceStore(
            harness.traces,
            crash_action_id="production.create_shot",
        )
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Bind the second task to state produced by its dependency",
            proposals=(
                AgentPlanStepProposal(
                    step_id="scene",
                    action_id="production.create_scene",
                    inputs={
                        "scene_id": "scene_execution_context",
                        "title": "Execution context scene",
                    },
                ),
                AgentPlanStepProposal(
                    step_id="shot",
                    action_id="production.create_shot",
                    inputs={
                        "shot_id": "shot_execution_context",
                        "scene_id": "scene_execution_context",
                        "intent": "Observe dependency-updated state",
                    },
                    dependencies=("scene",),
                ),
            ),
            plan_id="agent_plan_execution_context_recovery",
        )
        planning_context = state.plan.context_digest
        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        execution_context = harness.context.build(self.project.project_id).digest
        self.assertNotEqual(execution_context, planning_context)

        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="shot",
            )

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        self.assertEqual(reopened.tasks[1].status, AgentTaskStatus.SUCCEEDED)
        recovered_trace = next(
            trace
            for trace in reopened_harness.traces.list(self.project.project_id)
            if trace.action_id == "production.create_shot"
        )
        self.assertEqual(recovered_trace.context_digest, execution_context)
        self.assertNotEqual(recovered_trace.context_digest, planning_context)

    def test_reopen_recovers_generated_timeline_track_identity(self) -> None:
        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _CrashOnSuccessTraceStore(harness.traces)
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Create a track with an authority-generated identity",
            proposals=(
                AgentPlanStepProposal(
                    step_id="track",
                    action_id="timeline.create_track",
                    inputs={"kind": "video", "title": "Generated recovery track"},
                ),
            ),
            plan_id="agent_plan_generated_track_recovery",
        )
        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="track",
            )

        timeline = TimelineStore(self.store).load(self.project.project_id)
        self.assertEqual(len(timeline.tracks), 1)
        generated_track_id = timeline.tracks[0].track_id
        self.assertTrue(generated_track_id.startswith("trk_"))

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._empty_registry())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertEqual(task.result_references["track_id"], generated_track_id)
        recovered_trace = reopened_harness.traces.list(self.project.project_id)[0]
        self.assertEqual(
            recovered_trace.result_references["track_id"],
            generated_track_id,
        )

    def test_reopen_recovers_generated_timeline_clip_identity(self) -> None:
        source = self._register_video_source()
        TimelineCommandService(self.store).create_track(
            self.project.project_id,
            CreateTrackCommand(
                kind="video",
                title="Known track",
                track_id="track_recovery_known",
            ),
        )
        harness = AgentHarness(self.store, self._empty_registry())
        harness.traces = _CrashOnSuccessTraceStore(harness.traces)
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Add a clip with an authority-generated identity",
            proposals=(
                AgentPlanStepProposal(
                    step_id="clip",
                    action_id="timeline.add_clip",
                    inputs={
                        "track_id": "track_recovery_known",
                        "reference_id": source.id,
                        "timeline_start_us": 0,
                        "duration_us": 1_000_000,
                    },
                ),
            ),
            plan_id="agent_plan_generated_clip_recovery",
        )
        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="clip",
            )

        timeline = TimelineStore(self.store).load(self.project.project_id)
        track = timeline.track("track_recovery_known")
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
        self.assertEqual(task.result_references["track_id"], "track_recovery_known")
        self.assertEqual(task.result_references["clip_id"], generated_clip_id)
        recovered_trace = reopened_harness.traces.list(self.project.project_id)[0]
        self.assertEqual(
            recovered_trace.result_references["clip_id"],
            generated_clip_id,
        )

    def test_reopen_recovers_generation_submission_from_exact_durable_job(self) -> None:
        registry = self._local_generation_registry()
        harness = AgentHarness(self.store, registry)
        harness.traces = _CrashOnSuccessTraceStore(harness.traces)
        coordinator = AgentTaskCoordinator(harness)
        state = coordinator.create_plan(
            project_id=self.project.project_id,
            goal="Submit one generation and recover its durable Job",
            proposals=(
                AgentPlanStepProposal(
                    step_id="generate",
                    action_id="generation.submit",
                    inputs={
                        "shot_id": "shot_existing",
                        "model_id": "uv.image.commit_recovery",
                        "inputs": {"prompt": "recover exact durable job"},
                        "contract": GenerationContract().to_dict(),
                        "idempotency_key": "idem_stage16_commit_recovery",
                    },
                    target_shot_id="shot_existing",
                ),
            ),
            plan_id="agent_plan_generation_commit_recovery",
        )

        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="generate",
            )

        jobs = harness.jobs.list(self.project.project_id)
        self.assertEqual(len(jobs), 1)
        durable_running = coordinator.tasks.get(
            self.project.project_id,
            state.plan.plan_id,
            "generate",
        )
        self.assertEqual(durable_running.status, AgentTaskStatus.RUNNING)
        self.assertEqual(harness.traces.list(self.project.project_id), ())

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(
            reopened_store,
            self._local_generation_registry(),
        )
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertEqual(task.result_references["job_id"], jobs[0].job_id)
        self.assertIsNotNone(task.trace_id)
        self.assertEqual(len(reopened_harness.jobs.list(self.project.project_id)), 1)
        traces = reopened_harness.traces.list(self.project.project_id)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].result_references["job_id"], jobs[0].job_id)


if __name__ == "__main__":
    unittest.main()
