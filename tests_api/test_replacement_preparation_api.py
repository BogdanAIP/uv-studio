from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import get_execution_authorization_store
from uv_studio.api.mcp import get_mcp_manager
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import CostClass, LocalityClass, build_builtin_capability_registry
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.mcp.manager import MCPManager
from uv_studio.mcp.models import (
    MCPConfiguration,
    MCPProfile,
    MCPProjectFileOutput,
    MCPToolBinding,
)
from uv_studio.mcp.store import MCPConfigStore
from uv_studio.projects import (
    ContinuityEvidence,
    ProjectStore,
    RangeContinuityBrief,
    RangeContinuityBriefStore,
    ReplacementPlanProposal,
    ReplacementPlanStore,
)
from uv_studio.server import app

FIXTURE = Path(__file__).parents[1] / "tests" / "fixtures" / "mcp_test_server.py"


class ReplacementPreparationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_output_fixture = os.environ.get("UV_MCP_FIXTURE_PROJECT_OUTPUT_TOOL")
        os.environ["UV_MCP_FIXTURE_PROJECT_OUTPUT_TOOL"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root / "projects")
        self.project = self.store.create_project(title="Replacement preparation")
        self.project_dir = self.store.project_directory(self.project.project_id)
        (self.project_dir / "sources" / "source.mkv").write_bytes(b"source")
        self.registry = build_builtin_capability_registry()
        self.authorizations = OneShotAuthorizationStore()
        self.config_store = MCPConfigStore(self.root / "mcp-config")
        self.manager = MCPManager(self.config_store, self.registry)

        app.dependency_overrides[get_project_store] = lambda: self.store
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_execution_authorization_store] = lambda: self.authorizations
        app.dependency_overrides[get_mcp_manager] = lambda: self.manager
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()
        if self._old_output_fixture is None:
            os.environ.pop("UV_MCP_FIXTURE_PROJECT_OUTPUT_TOOL", None)
        else:
            os.environ["UV_MCP_FIXTURE_PROJECT_OUTPUT_TOOL"] = self._old_output_fixture

    def _brief(self) -> RangeContinuityBrief:
        return RangeContinuityBrief(
            edit_id="edit_1",
            source_path="sources/source.mkv",
            start_us=1_000_000,
            end_us=2_000_000,
            evidence=(
                ContinuityEvidence(
                    evidence_id="requested",
                    role="requested",
                    path="sources/source.mkv",
                    source_start_us=1_000_000,
                    source_end_us=2_000_000,
                ),
            ),
        )

    def _approve_plan(self, method_class: str) -> None:
        RangeContinuityBriefStore(self.store).upsert(self.project.project_id, self._brief())
        ReplacementPlanStore(self.store).approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class=method_class,
                goal="Prepare the approved replacement candidate.",
                required_changes=("Apply the requested replacement.",),
            ),
        )

    def _candidates_url(self) -> str:
        return f"/api/uv/projects/{self.project.project_id}/replacement-candidates"

    def _candidate_capability_url(self, stage: str, action: str) -> str:
        return (
            f"{self._candidates_url()}/edit_1/{stage}"
            f"/capabilities/video.generate/{action}"
        )

    def _configure_output_mcp(self) -> None:
        profile = MCPProfile(
            profile_id="fixture",
            title="Fixture",
            command=sys.executable,
            args=(str(FIXTURE),),
            startup_timeout_sec=10,
            discovery_timeout_sec=10,
        )
        binding = MCPToolBinding(
            binding_id="fixture.output",
            profile_id="fixture",
            tool_name="write_project_output",
            capability_id="video.generate",
            title="Fixture generated video",
            locality=LocalityClass.REMOTE,
            cost_class=CostClass.POTENTIALLY_PAID,
            asynchronous=True,
            project_file_outputs=(
                MCPProjectFileOutput(
                    argument_name="output_path",
                    media_kind="video",
                    suffix=".mp4",
                ),
            ),
        )
        self.config_store.save(MCPConfiguration(profiles=(profile,), bindings=(binding,)))
        asyncio.run(self.manager.connect("fixture"))

    @staticmethod
    def _acknowledgements() -> list[str]:
        return ["remote_execution", "external_cost", "unknown_cost"]

    def test_prepared_asset_creates_new_candidate_artifact_without_accepting_edit(self) -> None:
        self._approve_plan("prepared_asset")
        prepared = self.project_dir / "assets" / "replacement.mp4"
        prepared.write_bytes(b"prepared-video-bytes")

        response = self.client.post(
            f"{self._candidates_url()}/prepared-asset",
            json={"edit_id": "edit_1", "source_path": "assets/replacement.mp4"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        candidate = response.json()["candidate"]
        self.assertEqual(candidate["method_class"], "prepared_asset")
        self.assertEqual(candidate["stage"], "full")
        self.assertTrue(candidate["artifact_path"].startswith("artifacts/art_"))
        copied = self.project_dir / candidate["artifact_path"]
        self.assertEqual(copied.read_bytes(), prepared.read_bytes())
        self.assertNotEqual(copied.resolve(), prepared.resolve())
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

        listed = self.client.get(self._candidates_url())
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(len(listed.json()["candidates"]), 1)

        removed = self.client.delete(
            f"{self._candidates_url()}/{candidate['candidate_id']}"
        )
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(removed.json()["candidates"], [])
        self.assertTrue(copied.is_file())

    def test_prepared_asset_rejects_wrong_method_and_host_escape(self) -> None:
        self._approve_plan("deterministic_edit")
        wrong_method = self.client.post(
            f"{self._candidates_url()}/prepared-asset",
            json={"edit_id": "edit_1", "source_path": "sources/source.mkv"},
        )
        self.assertEqual(wrong_method.status_code, 409, wrong_method.text)
        self.assertEqual(wrong_method.json()["detail"]["code"], "method_class_mismatch")

        RangeContinuityBriefStore(self.store).remove(self.project.project_id, "edit_1")
        RangeContinuityBriefStore(self.store).upsert(self.project.project_id, self._brief())
        ReplacementPlanStore(self.store).approve(
            self.project.project_id,
            ReplacementPlanProposal(
                edit_id="edit_1",
                method_class="prepared_asset",
                goal="Prepare asset.",
                required_changes=("Use project asset.",),
            ),
        )
        escaped = self.client.post(
            f"{self._candidates_url()}/prepared-asset",
            json={"edit_id": "edit_1", "source_path": "../outside.mp4"},
        )
        self.assertEqual(escaped.status_code, 422, escaped.text)

    def test_remote_paid_mcp_sample_then_approved_full_uses_d017_and_owned_outputs(self) -> None:
        self._configure_output_mcp()
        self._approve_plan("generative_transform")
        offer_id = "mcp.fixture.output"
        sample_body = {
            "selection_policy": "pinned_offer",
            "offer_id": offer_id,
            "input": {"prompt": "sample candidate"},
        }

        prepared = self.client.post(
            self._candidate_capability_url("sample", "prepare-execution"),
            json=sample_body,
        )
        self.assertEqual(prepared.status_code, 200, prepared.text)
        self.assertEqual(
            prepared.json()["authorization"]["consent_required"],
            self._acknowledgements(),
        )
        plan_digest = prepared.json()["plan_sha256"]

        unauthorized = self.client.post(
            self._candidate_capability_url("sample", "execute"),
            json=sample_body,
        )
        self.assertEqual(unauthorized.status_code, 409, unauthorized.text)
        self.assertEqual(unauthorized.json()["detail"]["code"], "consent_required")

        authorized = self.client.post(
            self._candidate_capability_url("sample", "authorize-execution"),
            json={**sample_body, "acknowledgements": self._acknowledgements()},
        )
        self.assertEqual(authorized.status_code, 200, authorized.text)
        token = authorized.json()["authorization_token"]
        self.assertEqual(authorized.json()["plan_sha256"], plan_digest)

        sample_result = self.client.post(
            self._candidate_capability_url("sample", "execute"),
            json={**sample_body, "authorization_token": token},
        )
        self.assertEqual(sample_result.status_code, 200, sample_result.text)
        sample = sample_result.json()["candidate"]
        self.assertEqual(sample["stage"], "sample")
        self.assertEqual(sample["method_class"], "generative_transform")
        self.assertTrue(sample["execution_run_id"].startswith("run_"))
        self.assertEqual(sample["plan_sha256"], plan_digest)
        sample_artifact = self.project_dir / sample["artifact_path"]
        self.assertTrue(sample_artifact.is_file())
        self.assertGreater(sample_artifact.stat().st_size, 0)
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

        replay = self.client.post(
            self._candidate_capability_url("sample", "execute"),
            json={**sample_body, "authorization_token": token},
        )
        self.assertEqual(replay.status_code, 409, replay.text)
        self.assertEqual(replay.json()["detail"]["code"], "authorization_invalid")

        full_body = {
            "selection_policy": "pinned_offer",
            "offer_id": offer_id,
            "input": {"prompt": "full candidate"},
        }
        blocked_full = self.client.post(
            self._candidate_capability_url("full", "prepare-execution"),
            json=full_body,
        )
        self.assertEqual(blocked_full.status_code, 409, blocked_full.text)
        self.assertEqual(blocked_full.json()["detail"]["code"], "sample_approval_required")

        approved = self.client.post(
            f"{self._candidates_url()}/{sample['candidate_id']}/approve-sample",
            json={"candidate_id": sample["candidate_id"]},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(
            approved.json()["sample_approvals"][0]["candidate_id"],
            sample["candidate_id"],
        )

        full_auth = self.client.post(
            self._candidate_capability_url("full", "authorize-execution"),
            json={**full_body, "acknowledgements": self._acknowledgements()},
        )
        self.assertEqual(full_auth.status_code, 200, full_auth.text)
        full_token = full_auth.json()["authorization_token"]
        self.assertNotEqual(full_token, token)

        full_result = self.client.post(
            self._candidate_capability_url("full", "execute"),
            json={**full_body, "authorization_token": full_token},
        )
        self.assertEqual(full_result.status_code, 200, full_result.text)
        full = full_result.json()["candidate"]
        self.assertEqual(full["stage"], "full")
        self.assertEqual(full["plan_sha256"], plan_digest)
        self.assertNotEqual(full["artifact_path"], sample["artifact_path"])
        self.assertTrue((self.project_dir / full["artifact_path"]).is_file())
        self.assertFalse((self.project_dir / "timeline" / "range-edits.json").exists())

        project = self.store.load_project(self.project.project_id)
        self.assertEqual(len(project.artifacts), 2)
        serialized = json.dumps(project.to_dict())
        self.assertNotIn(str(self.root.resolve()), serialized)
        self.assertNotIn("fixture", serialized)
        self.assertNotIn(token, serialized)
        self.assertNotIn(full_token, serialized)

    def test_full_generative_preflight_blocks_before_authorization_if_sample_missing(self) -> None:
        self._configure_output_mcp()
        self._approve_plan("generative_transform")
        body = {
            "selection_policy": "pinned_offer",
            "offer_id": "mcp.fixture.output",
            "input": {"prompt": "full candidate"},
        }
        response = self.client.post(
            self._candidate_capability_url("full", "authorize-execution"),
            json={**body, "acknowledgements": self._acknowledgements()},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "sample_approval_required")
        self.assertEqual(list((self.project_dir / "tasks").glob("run_*.json")), [])
        self.assertEqual(list((self.project_dir / "artifacts").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
