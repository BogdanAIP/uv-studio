from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from uv_studio.mcp.client import (
    MCPInvocationError,
    MCPInvocationResponseTooLarge,
    MCPInvocationTimeout,
    MCPInvocationToolError,
    MCPInvocationToolMissing,
    MCPStdioDiscoveryClient,
)
from uv_studio.mcp.models import MCPProfile
from uv_studio.mcp.store import MCPConfigStore

FIXTURE = Path(__file__).parent / "fixtures" / "mcp_test_server.py"


class MCPInvocationTests(unittest.TestCase):
    def _profile(self, root: Path, exit_file: Path) -> MCPProfile:
        os.environ["UV_TEST_MCP_EXIT"] = str(exit_file)
        return MCPProfile(
            profile_id="fixture",
            title="Fixture",
            command=sys.executable,
            args=(str(FIXTURE),),
            env_refs=(("UV_MCP_FIXTURE_EXIT_FILE", "UV_TEST_MCP_EXIT"),),
            startup_timeout_sec=10,
            discovery_timeout_sec=10,
        )

    def tearDown(self) -> None:
        os.environ.pop("UV_TEST_MCP_EXIT", None)

    def test_real_call_tool_returns_structured_result_and_process_exits(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "exit.txt"
                client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                result = await client.invoke(
                    self._profile(root, exit_file),
                    tool_name="echo_metadata",
                    arguments={"text": "hello"},
                    timeout_sec=10,
                )
                self.assertFalse(result.get("isError", result.get("is_error", False)))
                structured = result.get("structuredContent", result.get("structured_content"))
                self.assertEqual(structured["echo"], "hello")
                self.assertTrue(exit_file.is_file())

        asyncio.run(scenario())

    def test_missing_tool_fails_closed_after_fresh_tool_list(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                with self.assertRaises(MCPInvocationToolMissing):
                    await client.invoke(
                        self._profile(root, root / "exit.txt"),
                        tool_name="not_reported",
                        arguments={},
                        timeout_sec=10,
                    )

        asyncio.run(scenario())

    def test_tool_error_is_normalized_after_sdk_cleanup(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "exit.txt"
                client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                with self.assertRaises(MCPInvocationToolError):
                    await client.invoke(
                        self._profile(root, exit_file),
                        tool_name="error_tool",
                        arguments={},
                        timeout_sec=10,
                    )
                self.assertTrue(exit_file.is_file())

        asyncio.run(scenario())

    def test_timeout_cleans_up_process(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "exit.txt"
                client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                with self.assertRaises(MCPInvocationTimeout):
                    await client.invoke(
                        self._profile(root, exit_file),
                        tool_name="slow_tool",
                        arguments={"delay": 2.0},
                        timeout_sec=0.2,
                    )
                self.assertTrue(exit_file.is_file())

        asyncio.run(scenario())

    def test_response_size_limit_is_enforced(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                with self.assertRaises(MCPInvocationResponseTooLarge):
                    await client.invoke(
                        self._profile(root, root / "exit.txt"),
                        tool_name="large_result",
                        arguments={"size": 20000},
                        timeout_sec=10,
                        max_response_bytes=4096,
                    )

        asyncio.run(scenario())

    def test_argument_size_limit_is_enforced_before_spawn(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                exit_file = root / "exit.txt"
                client = MCPStdioDiscoveryClient(MCPConfigStore(root / "config"))
                with self.assertRaises(MCPInvocationError):
                    await client.invoke(
                        self._profile(root, exit_file),
                        tool_name="echo_metadata",
                        arguments={"text": "x" * (300 * 1024)},
                        timeout_sec=10,
                    )
                self.assertFalse(exit_file.exists())

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
