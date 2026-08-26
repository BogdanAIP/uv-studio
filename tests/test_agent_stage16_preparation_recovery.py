from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStatus,
    AgentPlanStepProposal,
    AgentTaskCoordinator,
    AgentTaskStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.production.semantics import (
    PRODUCTION_SEMANTICS_DOCUMENT_ID,
    ProductionSemanticsDocument,
)
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class AgentStage16PreparationRecoveryTests(unittest.TestCase):
    def test_reopen_preserves_correlated_preparation_failure_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp) / "projects"
            store = ProjectStore(projects_root)
            project = store.create_project(
                title="Stage 16 preparation recovery",
                recipe_id=STUDIO_COMPAT_RECIPE_ID,
                extensions=studio_project_extensions("micro_drama"),
                project_id="prj_stage16_preparation_recovery",
            )
            models = ModelRegistry(CapabilityRegistry())
            production = ProductionSemanticService(store)
            production.create_scene(
                project.project_id,
                scene_id="target_scene",
                title="Target scene",
            )
            production.create_shot(
                project.project_id,
                shot_id="target_shot",
                scene_id="target_scene",
                intent="Target that will disappear before execution",
            )

            harness = AgentHarness(store, models)
            coordinator = AgentTaskCoordinator(harness)
            state = coordinator.create_plan(
                project_id=project.project_id,
                goal="Preserve a preparation failure across restart",
                proposals=(
                    AgentPlanStepProposal(
                        step_id="prep_failure",
                        action_id="production.create_scene",
                        inputs={
                            "scene_id": "scene_never_created",
                            "title": "Never created",
                        },
                        target_shot_id="target_shot",
                    ),
                ),
                plan_id="agent_plan_preparation_failure",
            )
            coordinator.tasks.transition(state.tasks[0], AgentTaskStatus.RUNNING)

            # Simulate the target disappearing after planning but before execution.
            production.documents.save(
                project.project_id,
                PRODUCTION_SEMANTICS_DOCUMENT_ID,
                ProductionSemanticsDocument().to_dict(),
            )

            spec = state.plan.task("prep_failure")
            expected_digest = coordinator._expected_input_digest(spec)
            with coordinator._correlated_traces.correlate(
                state.plan.plan_id,
                spec.task_id,
                spec.skill_id,
                expected_input_digest=expected_digest,
            ):
                with self.assertRaises(Exception):
                    harness.execute(
                        project_id=project.project_id,
                        action_id=spec.action_id,
                        inputs=dict(spec.inputs),
                        target_shot_id=spec.target_shot_id,
                    )

            traces = harness.traces.list(project.project_id)
            self.assertEqual(len(traces), 1)
            trace = traces[0]
            self.assertEqual(trace.input_digest, expected_digest)
            self.assertIn(state.plan.plan_id, trace.canonical_references)
            self.assertIn(spec.task_id, trace.canonical_references)

            reopened_store = ProjectStore(projects_root)
            reopened_harness = AgentHarness(
                reopened_store,
                ModelRegistry(CapabilityRegistry()),
            )
            reopened = AgentTaskCoordinator(reopened_harness)
            recovered = reopened.state(project.project_id, state.plan.plan_id)
            task = recovered.tasks[0]

            self.assertEqual(task.status, AgentTaskStatus.FAILED)
            self.assertEqual(recovered.status, AgentPlanStatus.FAILED)
            self.assertEqual(task.trace_id, trace.trace_id)
            self.assertNotIn("interrupted", task.error_message.lower())
            self.assertIn("shot", task.error_message.lower())
            self.assertEqual(len(reopened_harness.traces.list(project.project_id)), 1)


if __name__ == "__main__":
    unittest.main()
