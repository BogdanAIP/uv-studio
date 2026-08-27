from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStore,
    AgentSkillCatalog,
    AgentSubagentCoordinator,
    AgentSubagentError,
    AgentSubagentRequest,
    AgentSubagentRole,
    AgentTaskCoordinator,
    AgentTaskStatus,
)
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.production.commands import ProductionSemanticService
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class _StaticSubagentProvider:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload
        self.contexts = []

    def propose(self, context):
        self.contexts.append(context)
        return self.payload


class AgentFunctionalSubagentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Functional subagents",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_agent_subagents",
        )
        self.production = ProductionSemanticService(self.store)
        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_existing",
            title="Existing scene",
        )
        self.production.create_shot(
            self.project.project_id,
            shot_id="shot_existing",
            scene_id="scene_existing",
            intent="Existing target",
        )
        self.harness = AgentHarness(
            self.store,
            ModelRegistry(CapabilityRegistry()),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_role_catalog_is_bounded_and_explore_is_advisory(self) -> None:
        provider = _StaticSubagentProvider(
            {
                "summary": "The requested Shot exists in the bounded project context.",
                "findings": [
                    {
                        "finding_id": "finding_existing_shot",
                        "severity": "info",
                        "summary": "The target Shot is available for further work.",
                        "canonical_references": ["shot_existing"],
                    }
                ],
                "proposals": [],
            }
        )
        coordinator = AgentSubagentCoordinator(self.harness, provider)
        self.assertEqual(
            tuple(item.role for item in coordinator.catalog.list()),
            tuple(AgentSubagentRole),
        )
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.EXPLORE,
                project_id=self.project.project_id,
                objective="Inspect the existing target Shot",
                target_shot_id="shot_existing",
                canonical_references=("shot_existing",),
            )
        )
        self.assertEqual(result.request.role, AgentSubagentRole.EXPLORE)
        self.assertIsNone(result.validated_plan)
        self.assertEqual(result.findings[0].canonical_references, ("shot_existing",))
        self.assertEqual(provider.contexts[0].actions, ())
        self.assertEqual(
            AgentPlanStore(self.store).list(self.project.project_id),
            (),
        )

    def test_plan_role_must_pass_stage16_planner_and_does_not_mutate_on_delegate(self) -> None:
        provider = _StaticSubagentProvider(
            {
                "summary": "Create one bounded scene and shot through the existing Skill.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "setup",
                        "skill_id": AgentSkillCatalog.SCENE_WITH_SHOT,
                        "inputs": {
                            "scene_id": "scene_subagent",
                            "title": "Subagent scene",
                            "shot_id": "shot_subagent",
                            "intent": "Subagent shot",
                        },
                    }
                ],
            }
        )
        coordinator = AgentSubagentCoordinator(self.harness, provider)
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create a scene and its first shot",
            )
        )
        self.assertIsNotNone(result.validated_plan)
        assert result.validated_plan is not None
        self.assertEqual(
            tuple(task.task_id for task in result.validated_plan.tasks),
            ("setup.scene", "setup.shot"),
        )
        with self.assertRaises(Exception):
            self.production.state(self.project.project_id).scene("scene_subagent")
        self.assertEqual(AgentPlanStore(self.store).list(self.project.project_id), ())

        state = coordinator.persist_plan(result, plan_id="agent_plan_subagent")
        self.assertEqual(state.tasks[0].status, AgentTaskStatus.READY)
        self.assertEqual(state.tasks[1].status, AgentTaskStatus.PLANNED)
        with self.assertRaises(Exception):
            self.production.state(self.project.project_id).scene("scene_subagent")

        executor = AgentTaskCoordinator(self.harness)
        executor.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="setup.scene",
        )
        executor.execute_task(
            project_id=self.project.project_id,
            plan_id=state.plan.plan_id,
            task_id="setup.shot",
        )
        self.assertEqual(
            self.production.state(self.project.project_id).shot("shot_subagent").scene_id,
            "scene_subagent",
        )

    def test_media_role_cannot_escape_media_action_boundary(self) -> None:
        provider = _StaticSubagentProvider(
            {
                "summary": "Try an unrelated production mutation.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "wrong",
                        "action_id": "production.create_scene",
                        "inputs": {"scene_id": "scene_wrong", "title": "Wrong"},
                    }
                ],
            }
        )
        coordinator = AgentSubagentCoordinator(self.harness, provider)
        with self.assertRaisesRegex(AgentSubagentError, "media role cannot propose action"):
            coordinator.delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.MEDIA,
                    project_id=self.project.project_id,
                    objective="Prepare media work",
                )
            )

        valid_provider = _StaticSubagentProvider(
            {
                "summary": "Prepare a video track through the existing Timeline authority.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "video_track",
                        "action_id": "timeline.create_track",
                        "inputs": {"track_id": "media_video", "kind": "video"},
                    }
                ],
            }
        )
        valid = AgentSubagentCoordinator(self.harness, valid_provider).delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.MEDIA,
                project_id=self.project.project_id,
                objective="Prepare media work",
            )
        )
        self.assertEqual(valid.validated_plan.tasks[0].action_id, "timeline.create_track")

    def test_critic_reads_durable_plan_evidence_but_cannot_propose_repair(self) -> None:
        planning_provider = _StaticSubagentProvider(
            {
                "summary": "Create a bounded plan for critic inspection.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "critic_track",
                        "action_id": "timeline.create_track",
                        "inputs": {"track_id": "critic_video", "kind": "video"},
                    }
                ],
            }
        )
        planning = AgentSubagentCoordinator(self.harness, planning_provider)
        planned = planning.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create one track",
            )
        )
        state = planning.persist_plan(planned, plan_id="agent_plan_for_critic")

        critic_provider = _StaticSubagentProvider(
            {
                "summary": "The plan is durable and has one ready task.",
                "findings": [
                    {
                        "finding_id": "finding_ready_task",
                        "severity": "info",
                        "summary": "The plan has a task waiting for foreground execution.",
                        "canonical_references": ["agent_plan_for_critic"],
                    }
                ],
                "proposals": [],
            }
        )
        critic = AgentSubagentCoordinator(self.harness, critic_provider)
        result = critic.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.CRITIC,
                project_id=self.project.project_id,
                objective="Inspect the durable plan without repairing it",
                plan_id=state.plan.plan_id,
            )
        )
        evidence = critic_provider.contexts[0].evidence
        self.assertEqual(evidence["plan"]["plan_id"], "agent_plan_for_critic")
        self.assertEqual(evidence["tasks"][0]["status"], "ready")
        self.assertIsNone(result.validated_plan)

        repair_provider = _StaticSubagentProvider(
            {
                "summary": "Attempt a repair proposal.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "repair",
                        "action_id": "timeline.create_track",
                        "inputs": {"track_id": "repair_video", "kind": "video"},
                    }
                ],
            }
        )
        with self.assertRaisesRegex(AgentSubagentError, "advisory"):
            AgentSubagentCoordinator(self.harness, repair_provider).delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.CRITIC,
                    project_id=self.project.project_id,
                    objective="Try to repair the plan",
                    plan_id=state.plan.plan_id,
                )
            )

    def test_outputs_reject_hidden_fields_and_hallucinated_references(self) -> None:
        hidden_provider = _StaticSubagentProvider(
            {
                "summary": "Bounded summary",
                "findings": [],
                "proposals": [],
                "reasoning": "hidden chain should not enter the contract",
            }
        )
        with self.assertRaisesRegex(AgentSubagentError, "unsupported fields"):
            AgentSubagentCoordinator(self.harness, hidden_provider).delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.EXPLORE,
                    project_id=self.project.project_id,
                    objective="Inspect project",
                )
            )

        hallucinated_provider = _StaticSubagentProvider(
            {
                "summary": "Reference a nonexistent Shot.",
                "findings": [
                    {
                        "finding_id": "finding_missing",
                        "severity": "warning",
                        "summary": "This reference is not in bounded context.",
                        "canonical_references": ["shot_not_real"],
                    }
                ],
                "proposals": [],
            }
        )
        with self.assertRaisesRegex(AgentSubagentError, "absent from bounded subagent context"):
            AgentSubagentCoordinator(self.harness, hallucinated_provider).delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.EXPLORE,
                    project_id=self.project.project_id,
                    objective="Inspect project",
                )
            )

    def test_critic_requires_plan_id_and_other_roles_cannot_smuggle_one(self) -> None:
        with self.assertRaisesRegex(AgentSubagentError, "critic role requires plan_id"):
            AgentSubagentRequest(
                role=AgentSubagentRole.CRITIC,
                project_id=self.project.project_id,
                objective="Critique",
            )
        with self.assertRaisesRegex(AgentSubagentError, "only accepted by the critic"):
            AgentSubagentRequest(
                role=AgentSubagentRole.EXPLORE,
                project_id=self.project.project_id,
                objective="Explore",
                plan_id="agent_plan_other",
            )


if __name__ == "__main__":
    unittest.main()
