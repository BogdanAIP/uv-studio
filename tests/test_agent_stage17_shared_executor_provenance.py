from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentHarness,
    AgentPlanner,
    AgentPlanningError,
    AgentPlanStepProposal,
    AgentSubagentCoordinator,
    AgentSubagentRequest,
    AgentSubagentRole,
    AgentSubagentTaskCoordinator,
    AgentTaskCoordinator,
    AgentTaskStateError,
    AgentTaskStatus,
    AgentTraceRecord,
    AgentTraceStatus,
)
from uv_studio.agent.orchestration import AgentPlanner as LegacyAgentPlanner
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class _ScenePlanProposer:
    def __init__(self, scene_id: str) -> None:
        self.scene_id = scene_id

    def propose(self, context):
        return {
            "summary": "Create one scene through the bounded Stage-17 plan role.",
            "findings": [],
            "proposals": [
                {
                    "step_id": "scene",
                    "action_id": "production.create_scene",
                    "inputs": {
                        "scene_id": self.scene_id,
                        "title": "Shared executor provenance scene",
                    },
                }
            ],
        }


class _CrashOnSuccessTraceStore:
    """Simulate process loss after canonical commit but before success trace persistence."""

    def __init__(self, base: Any) -> None:
        self._base = base

    def append(self, record: AgentTraceRecord):
        if record.status is AgentTraceStatus.SUCCEEDED:
            raise SystemExit("simulated post-commit/pre-trace process loss")
        return self._base.append(record)

    def list(self, project_id: str):
        return self._base.list(project_id)


class AgentStage17SharedExecutorProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 17 shared executor provenance",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage17_shared_executor_provenance",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _models() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    @staticmethod
    def _scene_proposal(scene_id: str) -> AgentPlanStepProposal:
        return AgentPlanStepProposal(
            step_id="scene",
            action_id="production.create_scene",
            inputs={
                "scene_id": scene_id,
                "title": "Reference budget scene",
            },
        )

    @staticmethod
    def _references(count: int) -> tuple[str, ...]:
        return tuple(f"caller_ref_{index:03d}" for index in range(count))

    def _persist_scene_plan(self, harness: AgentHarness, *, scene_id: str, plan_id: str):
        coordinator = AgentSubagentCoordinator(harness, _ScenePlanProposer(scene_id))
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective=f"Create {scene_id} through Stage 17",
            )
        )
        state = coordinator.persist_plan(result, plan_id=plan_id)
        self.assertIn(result.delegation_id, state.plan.canonical_references)
        self.assertTrue(
            any(
                reference.startswith("agent_delegate_bind_")
                for reference in state.plan.canonical_references
            )
        )
        self.assertEqual(
            coordinator._task_coordinator._delegation_references(state.plan),
            (result.delegation_id,),
        )
        return coordinator, result, state

    def test_plain_stage16_executor_preserves_stage17_plan_provenance(self) -> None:
        harness = AgentHarness(self.store, self._models())
        _, result, state = self._persist_scene_plan(
            harness,
            scene_id="scene_shared_executor",
            plan_id="agent_plan_stage17_shared_executor",
        )

        executor = AgentTaskCoordinator(harness)
        executor.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="scene",
        )
        completed = executor.state(self.project.project_id, state.plan.plan_id)
        task = completed.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertIsNotNone(task.trace_id)

        trace = next(
            item
            for item in harness.traces.list(self.project.project_id)
            if item.trace_id == task.trace_id
        )
        self.assertIn(result.delegation_id, trace.canonical_references)

    def test_plain_stage16_reopen_recovery_preserves_stage17_plan_provenance(self) -> None:
        harness = AgentHarness(self.store, self._models())
        harness.traces = _CrashOnSuccessTraceStore(harness.traces)
        coordinator, result, state = self._persist_scene_plan(
            harness,
            scene_id="scene_shared_recovery",
            plan_id="agent_plan_stage17_shared_recovery",
        )

        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )
        self.assertEqual(harness.traces.list(self.project.project_id), ())

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._models())
        reopened = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            state.plan.plan_id,
        )
        task = reopened.tasks[0]
        self.assertEqual(task.status, AgentTaskStatus.SUCCEEDED)
        self.assertIsNotNone(task.trace_id)

        traces = reopened_harness.traces.list(self.project.project_id)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].trace_id, task.trace_id)
        self.assertIn(result.delegation_id, traces[0].canonical_references)

        production = ProductionSemanticService(reopened_store).state(self.project.project_id)
        self.assertEqual(
            len([scene for scene in production.scenes if scene.scene_id == "scene_shared_recovery"]),
            1,
        )

    def test_delegation_like_stage16_canonical_refs_are_not_stage17_origin(self) -> None:
        harness = AgentHarness(self.store, self._models())
        fake_refs = (
            "agent_delegate_media_11111111111111111111111111111111",
            "agent_delegate_plan_22222222222222222222222222222222",
        )
        legacy_plan = LegacyAgentPlanner(harness).build(
            project_id=self.project.project_id,
            goal="Ordinary Stage-16 plan with delegation-looking canonical IDs",
            proposals=(self._scene_proposal("scene_plain_stage16_fake_delegation"),),
            canonical_references=fake_refs,
            plan_id="agent_plan_plain_stage16_fake_delegation",
        )
        self.assertFalse(
            any(
                reference.startswith("agent_delegate_bind_")
                for reference in legacy_plan.canonical_references
            )
        )

        executor = AgentSubagentTaskCoordinator(harness)
        self.assertEqual(executor._delegation_references(legacy_plan), ())
        executor.plans.append(legacy_plan)
        executor.tasks.initialize(legacy_plan)
        executor.execute_task(
            project_id=self.project.project_id,
            plan_id=legacy_plan.plan_id,
            task_id="scene",
        )

        completed = executor.state(self.project.project_id, legacy_plan.plan_id)
        self.assertEqual(completed.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertIn(
            "scene_plain_stage16_fake_delegation",
            {scene.scene_id for scene in production.scenes},
        )

    def test_final_planner_reserves_terminal_reference_capacity(self) -> None:
        harness = AgentHarness(self.store, self._models())
        planner = AgentPlanner(harness)

        safe_plan = planner.build(
            project_id=self.project.project_id,
            goal="Execute at the final safe Plan reference boundary",
            proposals=(self._scene_proposal("scene_reference_budget_safe"),),
            canonical_references=self._references(111),
            plan_id="agent_plan_reference_budget_safe",
        )
        self.assertEqual(len(safe_plan.canonical_references), 112)

        executor = AgentTaskCoordinator(harness, planner=planner)
        executor.plans.append(safe_plan)
        executor.tasks.initialize(safe_plan)
        executor.execute_task(
            project_id=self.project.project_id,
            plan_id=safe_plan.plan_id,
            task_id="scene",
        )
        completed = executor.state(self.project.project_id, safe_plan.plan_id)
        self.assertEqual(completed.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        self.assertLessEqual(len(completed.tasks[0].canonical_references), 128)

        with self.assertRaisesRegex(
            AgentPlanningError,
            "execution-safe limit of 112",
        ):
            planner.build(
                project_id=self.project.project_id,
                goal="Reject a Plan that leaves no terminal reference reserve",
                proposals=(self._scene_proposal("scene_reference_budget_rejected"),),
                canonical_references=self._references(112),
                plan_id="agent_plan_reference_budget_rejected",
            )

        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertNotIn(
            "scene_reference_budget_rejected",
            {scene.scene_id for scene in production.scenes},
        )

    def test_legacy_oversized_plan_is_rejected_before_dispatch(self) -> None:
        harness = AgentHarness(self.store, self._models())
        legacy_plan = LegacyAgentPlanner(harness).build(
            project_id=self.project.project_id,
            goal="Simulate a previously persisted near-limit Plan",
            proposals=(self._scene_proposal("scene_legacy_reference_overflow"),),
            canonical_references=self._references(126),
            plan_id="agent_plan_legacy_reference_overflow",
        )
        self.assertEqual(len(legacy_plan.canonical_references), 127)

        executor = AgentTaskCoordinator(harness)
        executor.plans.append(legacy_plan)
        executor.tasks.initialize(legacy_plan)

        with self.assertRaisesRegex(
            AgentTaskStateError,
            "execution-safe limit of 112; dispatch refused",
        ):
            executor.execute_task(
                project_id=self.project.project_id,
                plan_id=legacy_plan.plan_id,
                task_id="scene",
            )

        task = executor.tasks.get(
            self.project.project_id,
            legacy_plan.plan_id,
            "scene",
        )
        self.assertEqual(task.status, AgentTaskStatus.READY)
        self.assertIsNone(task.started_at)
        self.assertEqual(harness.traces.list(self.project.project_id), ())

        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertNotIn(
            "scene_legacy_reference_overflow",
            {scene.scene_id for scene in production.scenes},
        )


if __name__ == "__main__":
    unittest.main()
