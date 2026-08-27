from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from uv_studio.agent import (
    AgentHarness,
    AgentSubagentCoordinator,
    AgentSubagentRequest,
    AgentSubagentRole,
    AgentTaskCoordinator,
    AgentTaskStatus,
    AgentTraceRecord,
    AgentTraceStatus,
)
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


if __name__ == "__main__":
    unittest.main()
