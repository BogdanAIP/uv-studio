from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.capabilities import get_capability_registry
from uv_studio.api.capability_execution import get_execution_authorization_store
from uv_studio.api.mcp import get_mcp_manager
from uv_studio.api.projects import get_project_store
from uv_studio.capabilities import (
    CostClass,
    LocalityClass,
    build_builtin_capability_registry,
)
from uv_studio.capabilities.authorization import OneShotAuthorizationStore
from uv_studio.mcp.manager import MCPManager
from uv_studio.mcp.models import MCPConfiguration, MCPProfile, MCPToolBinding
from uv_studio.mcp.store import MCPConfigStore
from uv_studio.projects.archive import export_project
from uv_studio.projects.store import ProjectStore
from uv_studio.server import app

FIXTURE = Path(__file__).parents[1] / "tests" / "fixtures" / "mcp_test_server.py"


class MCPExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.projects = ProjectStore(self.root / "projects")
        self.project = self.projects.create_project(title="MCP execution")
        self.registry = build_builtin_capability_registry()
        self.config_store = MCPConfigStore(self.root / "config")
        os.environ["UV_TEST_MCP_CALL_DELAY"] = "2"

        fixture_profile = MCPProfile(
            profile_id="fixture",
            title="Fixture",
            command=sys.executable,
            args=(str(FIXTURE),),
            startup_timeout_sec=10,
            discovery_timeout_sec=10,
        )
        slow_profile = MCPProfile(
            profile_id="slow_fixture",
            title="Slow fixture",
            command=sys.executable,
            args=(str(FIXTURE),),
            env_refs=(("UV_MCP_FIXTURE_CALL_DELAY", "UV_TEST_MCP_CALL_DELAY"),),
            startup_timeout_sec=10,
            discovery_timeout_sec=0.2,
        )
        bindings = (
            MCPToolBinding(
                binding_id="fixture.echo",
                profile_id="fixture",
                tool_name="echo_metadata",
                capability_id="media.understand",
                title="Fixture echo",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=False,
            ),
            MCPToolBinding(
                binding_id="fixture.cloud",
                profile_id="fixture",
                tool_name="cloud_generate",
                capability_id="video.generate",
                title="Fixture cloud",
                locality=LocalityClass.REMOTE,
                cost_class=CostClass.POTENTIALLY_PAID,
                asynchronous=True,
            ),
            MCPToolBinding(
                binding_id="fixture.fail",
                profile_id="fixture",
                tool_name="fail_tool",
                capability_id="media.understand",
                title="Fixture failure",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=False,
            ),
            MCPToolBinding(
                binding_id="fixture.slow",
                profile_id="slow_fixture",
                tool_name="slow_echo",
                capability_id="media.understand",
                title="Fixture slow",
                locality=LocalityClass.LOCAL,
                cost_class=CostClass.FREE,
                asynchronous=False,
            ),
        )
        self.config_store.save(
            MCPConfiguration(
                profiles=(fixture_profile, slow_profile),
                bindings=bindings,
            )
        )
        self.manager = MCPManager(self.config_store, self.registry)
        asyncio.run(self.manager.connect("fixture"))
        asyncio.run(self.manager.connect("slow_fixture"))
        self.authorizations = OneShotAuthorizationStore()

        app.dependency_overrides[get_project_store] = lambda: self.projects
        app.dependency_overrides[get_capability_registry] = lambda: self.registry
        app.dependency_overrides[get_mcp_manager] = lambda: self.manager
        app.dependency_overrides[get_execution_authorization_store] = lambda: self.authorizations
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        os.environ.pop("UV_TEST_MCP_CALL_DELAY", None)
        self.tmp.cleanup()

    def _url(self, capability_id: str, action: str = "execute") -> str:
        return (
            f"/api/uv/projects/{self.project.project_id}"
            f"/capabilities/{capability_id}/{action}"
        )

    def _records(self) -> list[dict]:
        task_dir = self.projects.project_directory(self.project.project_id) / "tasks"
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(task_dir.glob("run_*.json"))
        ]

    def test_exact_local_free_mcp_tool_executes_and_writes_success_provenance(self) -> None:
        response = self.client.post(
            self._url("media.understand"),
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.echo",
                "input": {"text": "hello"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        output = response.json()["result"]["output"]
        self.assertTrue(output["run_id"].startswith("run_"))
        self.assertIn("hello", output["mcp_result"]["content"][0]["text"])

        records = self._records()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["run_id"], output["run_id"])
        self.assertEqual(record["status"], "succeeded")
        self.assertEqual(record["profile_id"], "fixture")
        self.assertEqual(record["tool_name"], "echo_metadata")
        self.assertFalse(record["authorization"]["required"])
        self.assertEqual(record["authorization"]["consent_scopes"], [])
        self.assertIsNotNone(record["result_summary"]["sha256"])
        serialized = json.dumps(record)
        self.assertNotIn("authorization_token", serialized)
        self.assertNotIn("env_refs", serialized)

    def test_remote_potentially_paid_mcp_requires_one_shot_authorization(self) -> None:
        body = {
            "selection_policy": "pinned_offer",
            "offer_id": "mcp.fixture.cloud",
            "input": {"prompt": "hello cloud"},
        }
        blocked = self.client.post(self._url("video.generate"), json=body)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(blocked.json()["detail"]["code"], "consent_required")
        self.assertEqual(self._records(), [])

        authorized = self.client.post(
            self._url("video.generate", "authorize-execution"),
            json={
                **body,
                "acknowledgements": [
                    "remote_execution",
                    "external_cost",
                    "unknown_cost",
                ],
            },
        )
        self.assertEqual(authorized.status_code, 200, authorized.text)
        token = authorized.json()["authorization_token"]

        executed = self.client.post(
            self._url("video.generate"),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(executed.status_code, 200, executed.text)
        record = self._records()[0]
        self.assertEqual(record["status"], "succeeded")
        self.assertTrue(record["authorization"]["required"])
        self.assertEqual(
            record["authorization"]["consent_scopes"],
            ["remote_execution", "external_cost", "unknown_cost"],
        )
        self.assertEqual(record["cost"]["class"], "potentially_paid")
        self.assertEqual(record["cost"]["estimate"]["state"], "unknown")
        self.assertNotIn(token, json.dumps(record))

        replay = self.client.post(
            self._url("video.generate"),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(replay.status_code, 409, replay.text)
        self.assertEqual(replay.json()["detail"]["code"], "authorization_invalid")
        self.assertEqual(len(self._records()), 1)

    def test_tool_error_writes_failed_provenance_without_raw_error_content(self) -> None:
        response = self.client.post(
            self._url("media.understand"),
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.fail",
                "input": {},
            },
        )
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(response.json()["detail"]["code"], "mcp_tool_error")
        record = self._records()[0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error"]["code"], "mcp_tool_error")
        self.assertEqual(record["error"]["class"], "MCPToolReturnedError")
        serialized = json.dumps(record)
        self.assertNotIn("fixture failure", serialized)
        self.assertNotIn("stderr", serialized)

    def test_timeout_writes_failed_provenance(self) -> None:
        response = self.client.post(
            self._url("media.understand"),
            json={
                "selection_policy": "pinned_offer",
                "offer_id": "mcp.fixture.slow",
                "input": {},
            },
        )
        self.assertEqual(response.status_code, 504, response.text)
        self.assertEqual(response.json()["detail"]["code"], "mcp_call_timeout")
        record = self._records()[0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error"]["code"], "mcp_call_timeout")

    def test_archive_contains_provenance_but_not_authorization_token(self) -> None:
        body = {
            "selection_policy": "pinned_offer",
            "offer_id": "mcp.fixture.cloud",
            "input": {"prompt": "archive test"},
        }
        authorized = self.client.post(
            self._url("video.generate", "authorize-execution"),
            json={
                **body,
                "acknowledgements": [
                    "remote_execution",
                    "external_cost",
                    "unknown_cost",
                ],
            },
        )
        token = authorized.json()["authorization_token"]
        executed = self.client.post(
            self._url("video.generate"),
            json={**body, "authorization_token": token},
        )
        self.assertEqual(executed.status_code, 200, executed.text)

        archive_path = export_project(
            self.projects,
            self.project.project_id,
            self.root / "export.uvproj.zip",
        )
        with zipfile.ZipFile(archive_path) as archive:
            task_names = [
                name
                for name in archive.namelist()
                if name.startswith("project/tasks/run_") and name.endswith(".json")
            ]
            self.assertEqual(len(task_names), 1)
            archived_record = archive.read(task_names[0]).decode("utf-8")
            self.assertIn('"status": "succeeded"', archived_record)
            self.assertNotIn(token, archived_record)
            self.assertNotIn("authorization_token", archived_record)


if __name__ == "__main__":
    unittest.main()
