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
)
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


if __name__ == "__main__":
    unittest.main()
