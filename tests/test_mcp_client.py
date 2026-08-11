from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from uv_studio.mcp.client import (
    MAX_MCP_CALL_REQUEST_BYTES,
    MCPDiscoveryError,
    MCPDiscoveryTimeout,
    MCPMissingEnvironment,
    MCPRequestTooLarge,
    MCPResponseTooLarge,
    MCPStdioDiscoveryClient,
    MCPToolReturnedError,
    MCPCallTimeout,
)
from uv_studio.mcp.models import MCPProfile
from uv_studio.mcp.store import MCPConfigStore

FIXTURE = Path(__file__).parent / "fixtures" / "mcp_test_server.py"


class MCPStdioDiscoveryClientTests(unittest.TestCase):
    def test_real_stdio_discovery_lists_tools_and_process_exits(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "exit.txt"
                os.environ["UV_TEST_MCP_EXIT"] = str(exit_file)
                try:
                    profile = MCPProfile(
                        profile_id="fixture",
                        title="Fixture",
                        command=sys.executable,
                        args=(str(FIXTURE),),
                        env_refs=(("UV_MCP_FIXTURE_EXIT_FILE", "UV_TEST_MCP_EXIT"),),
                        startup_timeout_sec=10,
                        discovery_timeout_sec=10,
                    )
                    client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                    tools = await client.discover(profile)
                    self.assertEqual(
                        [tool.name for tool in tools],
                        [
                            "echo_metadata",
                            "cloud_generate",
                            "slow_echo",
                            "fail_tool",
                            "oversized_response",
                        ],
                    )
                    self.assertTrue(exit_file.is_file())
                    self.assertEqual(exit_file.read_text(encoding="utf-8").strip(), "stopped")
                finally:
                    os.environ.pop("UV_TEST_MCP_EXIT", None)

        asyncio.run(scenario())

    def test_real_stdio_call_tool_returns_json_safe_result_and_process_exits(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "call-exit.txt"
                os.environ["UV_TEST_MCP_EXIT"] = str(exit_file)
                try:
                    profile = MCPProfile(
                        profile_id="fixture_call",
                        title="Fixture call",
                        command=sys.executable,
                        args=(str(FIXTURE),),
                        env_refs=(("UV_MCP_FIXTURE_EXIT_FILE", "UV_TEST_MCP_EXIT"),),
                        startup_timeout_sec=10,
                        discovery_timeout_sec=10,
                    )
                    client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                    result = await client.call_tool(
                        profile,
                        "echo_metadata",
                        {"text": "hello"},
                    )
                    self.assertIsInstance(result, dict)
                    self.assertEqual(result["content"][0]["type"], "text")
                    self.assertIn("echo_metadata", result["content"][0]["text"])
                    self.assertIn("hello", result["content"][0]["text"])
                    self.assertTrue(exit_file.is_file())
                finally:
                    os.environ.pop("UV_TEST_MCP_EXIT", None)

        asyncio.run(scenario())

    def test_missing_environment_reference_fails_before_spawn(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                profile = MCPProfile(
                    profile_id="missing_env",
                    title="Missing env",
                    command=sys.executable,
                    args=(str(FIXTURE),),
                    env_refs=(("TOKEN", "UV_TEST_MCP_DOES_NOT_EXIST"),),
                )
                client = MCPStdioDiscoveryClient(MCPConfigStore(Path(tmp)))
                with self.assertRaises(MCPMissingEnvironment):
                    await client.discover(profile)

        asyncio.run(scenario())

    def test_discovery_timeout_cleans_up_stdio_server(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "timeout-exit.txt"
                os.environ["UV_TEST_MCP_EXIT"] = str(exit_file)
                os.environ["UV_TEST_MCP_DELAY"] = "2"
                try:
                    profile = MCPProfile(
                        profile_id="slow_fixture",
                        title="Slow fixture",
                        command=sys.executable,
                        args=(str(FIXTURE),),
                        env_refs=(
                            ("UV_MCP_FIXTURE_EXIT_FILE", "UV_TEST_MCP_EXIT"),
                            ("UV_MCP_FIXTURE_LIST_DELAY", "UV_TEST_MCP_DELAY"),
                        ),
                        startup_timeout_sec=10,
                        discovery_timeout_sec=0.2,
                    )
                    client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                    with self.assertRaises(MCPDiscoveryTimeout):
                        await client.discover(profile)
                    self.assertTrue(exit_file.is_file())
                finally:
                    os.environ.pop("UV_TEST_MCP_EXIT", None)
                    os.environ.pop("UV_TEST_MCP_DELAY", None)

        asyncio.run(scenario())

    def test_call_timeout_cleans_up_stdio_server(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "call-timeout-exit.txt"
                os.environ["UV_TEST_MCP_EXIT"] = str(exit_file)
                os.environ["UV_TEST_MCP_CALL_DELAY"] = "2"
                try:
                    profile = MCPProfile(
                        profile_id="slow_call",
                        title="Slow call",
                        command=sys.executable,
                        args=(str(FIXTURE),),
                        env_refs=(
                            ("UV_MCP_FIXTURE_EXIT_FILE", "UV_TEST_MCP_EXIT"),
                            ("UV_MCP_FIXTURE_CALL_DELAY", "UV_TEST_MCP_CALL_DELAY"),
                        ),
                        startup_timeout_sec=10,
                        discovery_timeout_sec=0.2,
                    )
                    client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                    with self.assertRaises(MCPCallTimeout):
                        await client.call_tool(profile, "slow_echo", {})
                    self.assertTrue(exit_file.is_file())
                finally:
                    os.environ.pop("UV_TEST_MCP_EXIT", None)
                    os.environ.pop("UV_TEST_MCP_CALL_DELAY", None)

        asyncio.run(scenario())

    def test_tool_error_is_structured_and_child_exits(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "tool-error-exit.txt"
                os.environ["UV_TEST_MCP_EXIT"] = str(exit_file)
                try:
                    profile = MCPProfile(
                        profile_id="error_call",
                        title="Error call",
                        command=sys.executable,
                        args=(str(FIXTURE),),
                        env_refs=(("UV_MCP_FIXTURE_EXIT_FILE", "UV_TEST_MCP_EXIT"),),
                    )
                    client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                    with self.assertRaises(MCPToolReturnedError) as caught:
                        await client.call_tool(profile, "fail_tool", {})
                    self.assertEqual(caught.exception.code, "mcp_tool_error")
                    self.assertTrue(exit_file.is_file())
                finally:
                    os.environ.pop("UV_TEST_MCP_EXIT", None)

        asyncio.run(scenario())

    def test_oversized_response_is_rejected(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                profile = MCPProfile(
                    profile_id="large_response",
                    title="Large response",
                    command=sys.executable,
                    args=(str(FIXTURE),),
                )
                client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                with self.assertRaises(MCPResponseTooLarge):
                    await client.call_tool(profile, "oversized_response", {})

        asyncio.run(scenario())

    def test_oversized_request_is_rejected_before_spawn(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                profile = MCPProfile(
                    profile_id="large_request",
                    title="Large request",
                    command="uv-studio-command-must-not-spawn",
                )
                client = MCPStdioDiscoveryClient(MCPConfigStore(Path(tmp)))
                with self.assertRaises(MCPRequestTooLarge):
                    await client.call_tool(
                        profile,
                        "echo_metadata",
                        {"text": "x" * (MAX_MCP_CALL_REQUEST_BYTES + 1)},
                    )

        asyncio.run(scenario())

    def test_missing_command_is_reported_without_command_details(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                profile = MCPProfile(
                    profile_id="broken_fixture",
                    title="Broken",
                    command="uv-studio-definitely-missing-mcp-command",
                    startup_timeout_sec=1,
                )
                client = MCPStdioDiscoveryClient(MCPConfigStore(Path(tmp)))
                with self.assertRaises(MCPDiscoveryError) as caught:
                    await client.discover(profile)
                self.assertNotIn("definitely-missing", str(caught.exception))

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
