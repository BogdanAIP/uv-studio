from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from uv_studio.api.mcp import get_mcp_manager
from uv_studio.capabilities import CostClass, LocalityClass, build_builtin_capability_registry
from uv_studio.mcp.manager import MCPManager
from uv_studio.mcp.models import (
    MCPConfiguration,
    MCPProfile,
    MCPToolBinding,
    MCPToolDescriptor,
)
from uv_studio.mcp.store import MCPConfigStore
from uv_studio.server import app


class FakeDiscoveryClient:
    async def discover(self, profile):
        return (
            MCPToolDescriptor(
                name="echo_metadata",
                title="Echo",
                description="Deterministic fixture tool",
                input_schema={"type": "object"},
            ),
        )


class MCPApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        store = MCPConfigStore(Path(self.tmp.name))
        profile = MCPProfile(
            profile_id="fixture",
            title="Fixture",
            command="python",
            env_refs=(("TOKEN", "UV_MCP_API_SECRET"),),
        )
        binding = MCPToolBinding(
            binding_id="fixture.echo",
            profile_id="fixture",
            tool_name="echo_metadata",
            capability_id="media.understand",
            title="Fixture echo",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=False,
        )
        store.save(MCPConfiguration(profiles=(profile,), bindings=(binding,)))
        self.registry = build_builtin_capability_registry()
        self.manager = MCPManager(
            store,
            self.registry,
            discovery_client=FakeDiscoveryClient(),
        )
        app.dependency_overrides[get_mcp_manager] = lambda: self.manager
        self.client = TestClient(app)
        os.environ["UV_MCP_API_SECRET"] = "never-return-this-value"

    def tearDown(self) -> None:
        os.environ.pop("UV_MCP_API_SECRET", None)
        app.dependency_overrides.clear()
        self.client.close()
        self.tmp.cleanup()

    def test_profiles_and_bindings_are_read_only_safe_metadata(self) -> None:
        profiles = self.client.get("/api/uv/mcp/profiles")
        self.assertEqual(profiles.status_code, 200, profiles.text)
        encoded = json.dumps(profiles.json())
        self.assertIn("UV_MCP_API_SECRET", encoded)
        self.assertNotIn("never-return-this-value", encoded)

        bindings = self.client.get("/api/uv/mcp/bindings")
        self.assertEqual(bindings.status_code, 200, bindings.text)
        self.assertEqual(bindings.json()[0]["capability_id"], "media.understand")

    def test_connect_lists_tools_and_registers_only_bound_offer(self) -> None:
        connected = self.client.post("/api/uv/mcp/profiles/fixture/connect")
        self.assertEqual(connected.status_code, 200, connected.text)
        self.assertEqual(connected.json()["state"], "ready")

        tools = self.client.get("/api/uv/mcp/profiles/fixture/tools")
        self.assertEqual(tools.status_code, 200, tools.text)
        self.assertEqual([tool["name"] for tool in tools.json()], ["echo_metadata"])

        offer = self.registry.get_offer("mcp.fixture.echo")
        self.assertEqual(offer.capability_id, "media.understand")
        self.assertEqual(offer.cost_class.value, "free")

    def test_disconnect_clears_ready_snapshot(self) -> None:
        self.assertEqual(
            self.client.post("/api/uv/mcp/profiles/fixture/connect").status_code,
            200,
        )
        stopped = self.client.post("/api/uv/mcp/profiles/fixture/disconnect")
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(stopped.json()["state"], "stopped")
        tools = self.client.get("/api/uv/mcp/profiles/fixture/tools")
        self.assertEqual(tools.status_code, 409, tools.text)

    def test_unknown_profile_is_404(self) -> None:
        response = self.client.get("/api/uv/mcp/profiles/missing/status")
        self.assertEqual(response.status_code, 404, response.text)

    def test_api_has_no_profile_creation_command_surface(self) -> None:
        response = self.client.post(
            "/api/uv/mcp/profiles",
            json={"profile_id": "evil", "command": "arbitrary"},
        )
        self.assertEqual(response.status_code, 405, response.text)


if __name__ == "__main__":
    unittest.main()
