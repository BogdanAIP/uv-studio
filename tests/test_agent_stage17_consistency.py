from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStore,
    AgentSubagentCoordinator,
    AgentSubagentError,
    AgentSubagentRequest,
    AgentSubagentRole,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class _StaticProposer:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload

    def propose(self, context):
        return self.payload


class _MutatingProposer:
    def __init__(self, production: ProductionSemanticService, project_id: str) -> None:
        self.production = production
        self.project_id = project_id

    def propose(self, context):
        self.production.create_scene(
            self.project_id,
            scene_id="scene_changed_during_delegate",
            title="Changed during delegate",
        )
        return {
            "summary": "This output was produced against stale context.",
            "findings": [],
            "proposals": [],
        }


class AgentStage17ConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 17 consistency",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage17_consistency",
        )
        self.production = ProductionSemanticService(self.store)
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_existing",
            title="Existing",
        )
        self.harness = AgentHarness(
            self.store,
            ModelRegistry(CapabilityRegistry()),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _plan_payload() -> dict[str, Any]:
        return {
            "summary": "Create one new Scene through the bounded Planner path.",
            "findings": [],
            "proposals": [
                {
                    "step_id": "create_scene",
                    "action_id": "production.create_scene",
                    "inputs": {
                        "scene_id": "scene_from_subagent",
                        "title": "From subagent",
                    },
                }
            ],
        }

    def test_delegate_fails_closed_when_role_context_changes_during_proposal(self) -> None:
        coordinator = AgentSubagentCoordinator(
            self.harness,
            _MutatingProposer(self.production, self.project.project_id),
        )
        with self.assertRaisesRegex(AgentSubagentError, "changed during delegation"):
            coordinator.delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.EXPLORE,
                    project_id=self.project.project_id,
                    objective="Inspect the project",
                )
            )

    def test_persist_rejects_stale_plan_role_result_after_project_change(self) -> None:
        coordinator = AgentSubagentCoordinator(
            self.harness,
            _StaticProposer(self._plan_payload()),
        )
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create a new Scene",
            )
        )
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_intervening",
            title="Intervening mutation",
        )

        with self.assertRaisesRegex(AgentSubagentError, "changed since delegation"):
            coordinator.persist_plan(result, plan_id="agent_plan_stale_subagent")
        self.assertEqual(
            AgentPlanStore(self.store).list(self.project.project_id),
            (),
        )

    def test_unchanged_context_can_persist_through_existing_stage16_authority(self) -> None:
        coordinator = AgentSubagentCoordinator(
            self.harness,
            _StaticProposer(self._plan_payload()),
        )
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create a new Scene",
            )
        )
        state = coordinator.persist_plan(result, plan_id="agent_plan_fresh_subagent")
        self.assertEqual(state.plan.plan_id, "agent_plan_fresh_subagent")
        self.assertEqual(
            tuple(item.plan_id for item in AgentPlanStore(self.store).list(self.project.project_id)),
            ("agent_plan_fresh_subagent",),
        )


if __name__ == "__main__":
    unittest.main()
