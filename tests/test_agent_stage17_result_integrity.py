from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from uv_studio.agent import (
    AgentHarness,
    AgentPlanStepProposal,
    AgentPlanStore,
    AgentSubagentCoordinator,
    AgentSubagentError,
    AgentSubagentRequest,
    AgentSubagentResult,
    AgentSubagentRole,
    AgentSubagentTaskCoordinator,
    AgentTaskStatus,
)
from uv_studio.agent.stage16_generation_target import AgentPlanner
from uv_studio.agent.stage17_provenance import _delegation_id
from uv_studio.agent.subagents import AgentSubagentResult as BaseAgentSubagentResult
from uv_studio.capabilities.registry import CapabilityRegistry
from uv_studio.generation.models import ModelRegistry
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.store import ProjectStore


class _MediaProposer:
    def propose(self, context):
        return {
            "summary": "Create one bounded video track.",
            "findings": [],
            "proposals": [
                {
                    "step_id": "video_track",
                    "action_id": "timeline.create_track",
                    "inputs": {"track_id": "integrity_video", "kind": "video"},
                }
            ],
        }


class AgentStage17ResultIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.store.create_project(
            title="Stage 17 result integrity",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_stage17_result_integrity",
        )
        self.harness = AgentHarness(
            self.store,
            ModelRegistry(CapabilityRegistry()),
        )
        self.coordinator = AgentSubagentCoordinator(self.harness, _MediaProposer())
        self.request = AgentSubagentRequest(
            role=AgentSubagentRole.MEDIA,
            project_id=self.project.project_id,
            objective="Prepare bounded media work",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _models() -> ModelRegistry:
        return ModelRegistry(CapabilityRegistry())

    def test_content_addressed_result_rejects_post_delegate_tampering(self) -> None:
        result = self.coordinator.delegate(self.request)
        with self.assertRaisesRegex(
            AgentSubagentError,
            "delegation_id does not match validated result content",
        ):
            replace(result, summary="tampered after delegation")
        self.assertEqual(AgentPlanStore(self.store).list(self.project.project_id), ())

    def test_persist_plan_revalidates_media_role_for_exactly_addressed_result(self) -> None:
        delegated = self.coordinator.delegate(self.request)
        forbidden = AgentPlanStepProposal(
            step_id="forbidden_scene",
            action_id="production.create_scene",
            inputs={
                "scene_id": "scene_media_bypass",
                "title": "Must not be created by media role",
            },
        )
        base = BaseAgentSubagentResult(
            request=delegated.request,
            context_digest=delegated.context_digest,
            summary="Forged but content-addressed media result",
            findings=(),
            proposals=(forbidden,),
            validated_plan=None,
            schema_version=delegated.schema_version,
        )
        forged = AgentSubagentResult(
            request=base.request,
            context_digest=base.context_digest,
            summary=base.summary,
            findings=base.findings,
            proposals=base.proposals,
            validated_plan=None,
            schema_version=base.schema_version,
            delegation_id=_delegation_id(base),
        )

        with self.assertRaisesRegex(
            AgentSubagentError,
            "media role cannot propose action 'production.create_scene'",
        ):
            self.coordinator.persist_plan(
                forged,
                plan_id="agent_plan_media_role_bypass",
            )
        self.assertEqual(AgentPlanStore(self.store).list(self.project.project_id), ())

    def test_prefix_like_canonical_project_id_is_not_a_delegation_reference(self) -> None:
        project = self.store.create_project(
            title="Delegation prefix collision",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="agent_delegate_project",
        )
        harness = AgentHarness(self.store, self._models())
        coordinator = AgentSubagentCoordinator(harness, _MediaProposer())
        result = coordinator.delegate(
            AgentSubagentRequest(
                role=AgentSubagentRole.MEDIA,
                project_id=project.project_id,
                objective="Create a track without confusing the project ID for delegation provenance",
            )
        )
        state = coordinator.persist_plan(
            result,
            plan_id="agent_plan_prefix_collision",
        )
        self.assertIn(project.project_id, state.plan.canonical_references)
        self.assertIn(result.delegation_id, state.plan.canonical_references)

        coordinator.execute_task(
            project_id=project.project_id,
            plan_id=state.plan.plan_id,
            task_id="video_track",
        )
        reopened = AgentSubagentTaskCoordinator(harness).state(
            project.project_id,
            state.plan.plan_id,
        )
        self.assertEqual(reopened.tasks[0].status, AgentTaskStatus.SUCCEEDED)
        self.assertIn(result.delegation_id, reopened.tasks[0].canonical_references)

    def test_complete_delegation_namespace_is_reserved_from_canonical_project_ids(self) -> None:
        project = self.store.create_project(
            title="Typed delegation collision",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="agent_delegate_media_00000000000000000000000000000000",
        )
        harness = AgentHarness(self.store, self._models())
        coordinator = AgentSubagentCoordinator(harness, _MediaProposer())

        with self.assertRaisesRegex(
            AgentSubagentError,
            "reserved functional-subagent delegation namespace",
        ):
            coordinator.delegate(
                AgentSubagentRequest(
                    role=AgentSubagentRole.MEDIA,
                    project_id=project.project_id,
                    objective="Reject a canonical identity that occupies the delegation namespace",
                )
            )
        self.assertEqual(AgentPlanStore(self.store).list(project.project_id), ())

    def test_injected_task_coordinator_must_share_exact_harness_authority(self) -> None:
        foreign_store = ProjectStore(Path(self.tmp.name) / "foreign-projects")
        foreign_store.create_project(
            title="Foreign authority",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id=self.project.project_id,
        )
        foreign_harness = AgentHarness(foreign_store, self._models())
        foreign_tasks = AgentSubagentTaskCoordinator(foreign_harness)

        with self.assertRaisesRegex(
            AgentSubagentError,
            "share the exact AgentHarness and Project Store authority",
        ):
            AgentSubagentCoordinator(
                self.harness,
                _MediaProposer(),
                task_coordinator=foreign_tasks,
            )

    def test_standalone_planner_must_share_exact_harness_authority(self) -> None:
        foreign_store = ProjectStore(Path(self.tmp.name) / "foreign-planner-projects")
        foreign_store.create_project(
            title="Foreign planner authority",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id=self.project.project_id,
        )
        foreign_harness = AgentHarness(foreign_store, self._models())
        foreign_planner = AgentPlanner(foreign_harness)

        with self.assertRaisesRegex(
            AgentSubagentError,
            "planner must share the exact AgentHarness authority",
        ):
            AgentSubagentCoordinator(
                self.harness,
                _MediaProposer(),
                planner=foreign_planner,
            )
        self.assertEqual(AgentPlanStore(self.store).list(self.project.project_id), ())

    def test_same_harness_standalone_planner_is_accepted(self) -> None:
        planner = AgentPlanner(self.harness)
        coordinator = AgentSubagentCoordinator(
            self.harness,
            _MediaProposer(),
            planner=planner,
        )
        self.assertIs(coordinator.planner, planner)

    def test_same_harness_injected_task_coordinator_shares_exact_planner(self) -> None:
        task_coordinator = AgentSubagentTaskCoordinator(self.harness)
        coordinator = AgentSubagentCoordinator(
            self.harness,
            _MediaProposer(),
            task_coordinator=task_coordinator,
        )
        self.assertIs(coordinator.planner, task_coordinator.planner)


if __name__ == "__main__":
    unittest.main()
