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
    AgentSubagentTaskCoordinator,
    AgentTaskStatus,
    AgentTraceRecord,
    AgentTraceStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class _StaticPlanProposer:
    def propose(self, context):
        return {
            "summary": "Create one scene through the bounded Stage-17 plan role.",
            "findings": [],
            "proposals": [
                {
                    "step_id": "scene",
                    "action_id": "production.create_scene",
                    "inputs": {
                        "scene_id": "scene_stage17_recovery",
                        "title": "Recovered Stage 17 scene",
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
            raise SystemExit("simulated Stage-17 post-commit/pre-trace process loss")
        return self._base.append(record)

    def list(self, project_id: str):
        return self._base.list(project_id)


class AgentStage17RecoveryProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.tmp.name) / "projects"
        self.store = ProjectStore(self.projects_root)
        self.project = self.store.create_project(
            title="Stage 17 recovery provenance",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage17_recovery_provenance",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _models() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    def test_reopen_recovery_keeps_delegation_reference_in_reconstructed_trace(self) -> None:
        harness = AgentHarness(self.store, self._models())
        harness.traces = _CrashOnSuccessTraceStore(harness.traces)
        coordinator = AgentSubagentCoordinator(harness, _StaticPlanProposer())
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create one scene and survive trace-loss recovery",
            )
        )
        state = coordinator.persist_plan(
            result,
            plan_id="agent_plan_stage17_recovery_provenance",
        )
        self.assertIn(result.delegation_id, state.plan.canonical_references)

        with self.assertRaises(SystemExit):
            coordinator.execute_task(
                project_id=self.project.project_id,
                plan_id=state.plan.plan_id,
                task_id="scene",
            )

        self.assertEqual(harness.traces.list(self.project.project_id), ())
        production = ProductionSemanticService(self.store).state(self.project.project_id)
        self.assertEqual(
            production.scene("scene_stage17_recovery").title,
            "Recovered Stage 17 scene",
        )

        reopened_store = ProjectStore(self.projects_root)
        reopened_harness = AgentHarness(reopened_store, self._models())
        reopened = AgentSubagentTaskCoordinator(reopened_harness).state(
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
        self.assertIn(result.delegation_id, task.canonical_references)

        production_after = ProductionSemanticService(reopened_store).state(
            self.project.project_id
        )
        self.assertEqual(
            len(
                [
                    scene
                    for scene in production_after.scenes
                    if scene.scene_id == "scene_stage17_recovery"
                ]
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
