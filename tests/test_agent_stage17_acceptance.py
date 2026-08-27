from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStore,
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


class _RoleFlowProposer:
    def __init__(self) -> None:
        self.contexts = []

    def propose(self, context):
        self.contexts.append(context)
        role = context.request.role
        if role is AgentSubagentRole.EXPLORE:
            return {
                "summary": "The existing Shot is available for bounded planning.",
                "findings": [
                    {
                        "finding_id": "finding_existing",
                        "severity": "info",
                        "summary": "Use the existing Shot as the starting production context.",
                        "canonical_references": ["shot_existing"],
                    }
                ],
                "proposals": [],
            }
        if role is AgentSubagentRole.PLAN:
            return {
                "summary": "Create a dependent Scene and Shot through Stage-16 authorities.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "scene",
                        "action_id": "production.create_scene",
                        "inputs": {
                            "scene_id": "scene_role_flow",
                            "title": "Role flow scene",
                        },
                    },
                    {
                        "step_id": "shot",
                        "action_id": "production.create_shot",
                        "inputs": {
                            "shot_id": "shot_role_flow",
                            "scene_id": "scene_role_flow",
                            "intent": "Role flow shot",
                        },
                        "dependencies": ["scene"],
                    },
                ],
            }
        if role is AgentSubagentRole.MEDIA:
            return {
                "summary": "Prepare one bounded video track through the Timeline authority.",
                "findings": [],
                "proposals": [
                    {
                        "step_id": "video_track",
                        "action_id": "timeline.create_track",
                        "inputs": {"track_id": "role_flow_video", "kind": "video"},
                    }
                ],
            }
        if role is AgentSubagentRole.CRITIC:
            delegation_refs = [
                item
                for item in context.available_references
                if item.startswith("agent_delegate_media_")
            ]
            if len(delegation_refs) != 1:
                raise AssertionError(
                    f"expected one durable media delegation reference, got {delegation_refs!r}"
                )
            return {
                "summary": "The durable media task and trace preserve delegation provenance.",
                "findings": [
                    {
                        "finding_id": "finding_media_provenance",
                        "severity": "info",
                        "summary": "The media delegation remains linked after reopen.",
                        "canonical_references": delegation_refs,
                    }
                ],
                "proposals": [],
            }
        raise AssertionError(f"unexpected role: {role!r}")


class _FailingProposer:
    def propose(self, context):
        raise RuntimeError("bounded proposer failure")


class _OversizedProposer:
    def propose(self, context):
        return {
            "summary": "x" * (33 * 1024),
            "findings": [],
            "proposals": [],
        }


class AgentStage17AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 17 acceptance",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage17_acceptance",
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

    def test_foreground_multi_role_flow_preserves_delegation_through_reopen(self) -> None:
        proposer = _RoleFlowProposer()
        coordinator = AgentSubagentCoordinator(self.harness, proposer)

        explored = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.EXPLORE,
                project_id=self.project.project_id,
                objective="Inspect the existing production target",
                target_shot_id="shot_existing",
                canonical_references=("shot_existing",),
            )
        )
        self.assertTrue(explored.delegation_id.startswith("agent_delegate_explore_"))
        self.assertEqual(explored.findings[0].canonical_references, ("shot_existing",))

        planned = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.PLAN,
                project_id=self.project.project_id,
                objective="Create a dependent Scene and Shot",
            )
        )
        self.assertTrue(planned.delegation_id.startswith("agent_delegate_plan_"))
        self.assertIsNotNone(planned.validated_plan)
        assert planned.validated_plan is not None
        self.assertIn(planned.delegation_id, planned.validated_plan.canonical_references)
        self.assertEqual(planned.validated_plan.task("shot").dependencies, ("scene",))

        plan_state = coordinator.persist_plan(planned, plan_id="agent_plan_role_flow")
        self.assertIn(planned.delegation_id, plan_state.plan.canonical_references)
        self.assertEqual(plan_state.tasks[0].status, AgentTaskStatus.READY)
        self.assertEqual(plan_state.tasks[1].status, AgentTaskStatus.PLANNED)
        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=plan_state.plan.plan_id,
            task_id="scene",
        )
        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=plan_state.plan.plan_id,
            task_id="shot",
        )
        self.assertEqual(
            self.production.state(self.project.project_id).shot("shot_role_flow").scene_id,
            "scene_role_flow",
        )

        media = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.MEDIA,
                project_id=self.project.project_id,
                objective="Prepare bounded media work",
                target_shot_id="shot_role_flow",
                canonical_references=("shot_role_flow",),
            )
        )
        self.assertTrue(media.delegation_id.startswith("agent_delegate_media_"))
        media_state = coordinator.persist_plan(media, plan_id="agent_plan_media_role_flow")
        self.assertIn(media.delegation_id, media_state.plan.canonical_references)
        coordinator.execute_task(
            project_id=self.project.project_id,
            plan_id=media_state.plan.plan_id,
            task_id="video_track",
        )

        completed_media = AgentTaskCoordinator(self.harness).state(
            self.project.project_id,
            media_state.plan.plan_id,
        )
        self.assertEqual(completed_media.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        trace_id = completed_media.tasks[0].trace_id
        assert trace_id is not None
        trace = next(
            item
            for item in self.harness.traces.list(self.project.project_id)
            if item.trace_id == trace_id
        )
        self.assertIn(media.delegation_id, trace.canonical_references)

        reopened_store = ProjectStore(self.store.root)
        reopened_harness = AgentHarness(
            reopened_store,
            ModelRegistry(CapabilityRegistry()),
        )
        reopened_state = AgentTaskCoordinator(reopened_harness).state(
            self.project.project_id,
            media_state.plan.plan_id,
        )
        self.assertEqual(reopened_state.tasks[0].trace_id, trace_id)
        self.assertIn(media.delegation_id, reopened_state.plan.canonical_references)

        critic = AgentSubagentCoordinator(reopened_harness, proposer).delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.CRITIC,
                project_id=self.project.project_id,
                objective="Inspect the durable media result without repairing it",
                plan_id=media_state.plan.plan_id,
            )
        )
        self.assertTrue(critic.delegation_id.startswith("agent_delegate_critic_"))
        self.assertEqual(
            critic.findings[0].canonical_references,
            (media.delegation_id,),
        )

    def test_failed_or_oversized_role_work_creates_no_durable_plan(self) -> None:
        failing = AgentSubagentCoordinator(self.harness, _FailingProposer())
        with self.assertRaisesRegex(AgentSubagentError, "proposer failed"):
            failing.delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.PLAN,
                    project_id=self.project.project_id,
                    objective="Do not persist failed role work",
                )
            )
        self.assertEqual(AgentPlanStore(self.store).list(self.project.project_id), ())

        oversized = AgentSubagentCoordinator(self.harness, _OversizedProposer())
        with self.assertRaisesRegex(AgentSubagentError, "serialized bytes"):
            oversized.delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.EXPLORE,
                    project_id=self.project.project_id,
                    objective="Reject oversized output",
                )
            )
        self.assertEqual(AgentPlanStore(self.store).list(self.project.project_id), ())

        with self.assertRaisesRegex(AgentSubagentError, "unknown functional subagent role"):
            AgentSubagentRequest(
                role="unknown-role",
                project_id=self.project.project_id,
                objective="Reject an unknown role",
            )


if __name__ == "__main__":
    unittest.main()
