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


class _StaticSubagentProposer:
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
        proposer = _StaticSubagentProposer(
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
        coordinator = AgentSubagentCoordinator(self.harness, proposer)
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
        self.assertEqual(proposer.contexts[0].actions, ())
        self.assertEqual(proposer.contexts[0].skills, ())
        self.assertIn("shot_existing", proposer.contexts[0].available_references)
        self.assertEqual(
            AgentPlanStore(self.store).list(self.project.project_id),
            (),
        )

    def test_plan_role_sees_bounded_skills_and_must_pass_stage16_planner(self) -> None:
        proposer = _StaticSubagentProposer(
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
        coordinator = AgentSubagentCoordinator(self.harness, proposer)
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create a scene and its first shot",
            )
        )
        skill_ids = tuple(item["skill_id"] for item in proposer.contexts[0].skills)
        self.assertEqual(skill_ids, (AgentSkillCatalog.SCENE_WITH_SHOT,))
        self.assertIsNotNone(result.validated_plan)
        assert result.validated_plan is not None
        self.assertEqual(
            tuple(task.task_id for task in result.validated_plan.tasks),
            ("setup.scene", "setup.shot"),
        )
        self.assertFalse(
            any(scene.scene_id == "scene_subagent" for scene in self.production.state(self.project.project_id).scenes)
        )
        self.assertEqual(AgentPlanStore(self.store).list(self.project.project_id), ())

        state = coordinator.persist_plan(result, plan_id="agent_plan_subagent")
        self.assertEqual(state.tasks[0].status, AgentTaskStatus.READY)
        self.assertEqual(state.tasks[1].status, AgentTaskStatus.PLANNED)
        self.assertFalse(
            any(scene.scene_id == "scene_subagent" for scene in self.production.state(self.project.project_id).scenes)
        )

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

    def test_media_role_cannot_escape_media_action_or_skill_boundary(self) -> None:
        proposer = _StaticSubagentProposer(
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
        coordinator = AgentSubagentCoordinator(self.harness, proposer)
        with self.assertRaisesRegex(AgentSubagentError, "media role cannot propose action"):
            coordinator.delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.MEDIA,
                    project_id=self.project.project_id,
                    objective="Prepare media work",
                )
            )

        skill_proposer = _StaticSubagentProposer(
            {
                "summary": "Try to expand a general Skill.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "wrong_skill",
                        "skill_id": AgentSkillCatalog.SCENE_WITH_SHOT,
                        "inputs": {
                            "scene_id": "scene_wrong_skill",
                            "title": "Wrong skill",
                            "shot_id": "shot_wrong_skill",
                            "intent": "Wrong skill",
                        },
                    }
                ],
            }
        )
        with self.assertRaisesRegex(AgentSubagentError, "media role cannot propose Skill"):
            AgentSubagentCoordinator(self.harness, skill_proposer).delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.MEDIA,
                    project_id=self.project.project_id,
                    objective="Prepare media work",
                )
            )

        valid_proposer = _StaticSubagentProposer(
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
        valid = AgentSubagentCoordinator(self.harness, valid_proposer).delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.MEDIA,
                project_id=self.project.project_id,
                objective="Prepare media work",
            )
        )
        self.assertEqual(valid.validated_plan.tasks[0].action_id, "timeline.create_track")

    def test_critic_reads_durable_plan_evidence_but_cannot_propose_repair(self) -> None:
        planning_proposer = _StaticSubagentProposer(
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
        planning = AgentSubagentCoordinator(self.harness, planning_proposer)
        planned = planning.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create one track",
            )
        )
        state = planning.persist_plan(planned, plan_id="agent_plan_for_critic")

        critic_proposer = _StaticSubagentProposer(
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
        critic = AgentSubagentCoordinator(self.harness, critic_proposer)
        result = critic.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.CRITIC,
                project_id=self.project.project_id,
                objective="Inspect the durable plan without repairing it",
                plan_id=state.plan.plan_id,
            )
        )
        evidence = critic_proposer.contexts[0].evidence
        self.assertEqual(evidence["plan"]["plan_id"], "agent_plan_for_critic")
        self.assertEqual(evidence["tasks"][0]["status"], "ready")
        self.assertIn("agent_plan_for_critic", critic_proposer.contexts[0].available_references)
        self.assertIsNone(result.validated_plan)

        repair_proposer = _StaticSubagentProposer(
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
            AgentSubagentCoordinator(self.harness, repair_proposer).delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.CRITIC,
                    project_id=self.project.project_id,
                    objective="Try to repair the plan",
                    plan_id=state.plan.plan_id,
                )
            )

    def test_outputs_reject_hidden_fields_and_non_reference_strings(self) -> None:
        hidden_proposer = _StaticSubagentProposer(
            {
                "summary": "Bounded summary",
                "findings": [],
                "proposals": [],
                "reasoning": "hidden chain should not enter the contract",
            }
        )
        with self.assertRaisesRegex(AgentSubagentError, "unsupported fields"):
            AgentSubagentCoordinator(self.harness, hidden_proposer).delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.EXPLORE,
                    project_id=self.project.project_id,
                    objective="Inspect project",
                )
            )

        self.production.create_scene(
            self.project.project_id,
            scene_id="scene_title_probe",
            title="shot_not_real",
        )
        hallucinated_proposer = _StaticSubagentProposer(
            {
                "summary": "Reference a title that only looks like an ID.",
                "findings": [
                    {
                        "finding_id": "finding_missing",
                        "severity": "warning",
                        "summary": "This string is a title, not a canonical reference.",
                        "canonical_references": ["shot_not_real"],
                    }
                ],
                "proposals": [],
            }
        )
        with self.assertRaisesRegex(AgentSubagentError, "absent from bounded subagent context"):
            AgentSubagentCoordinator(self.harness, hallucinated_proposer).delegate(
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
