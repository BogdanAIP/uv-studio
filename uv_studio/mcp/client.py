"""Bounded read-only MCP stdio discovery using the official Python SDK v2."""

from __future__ import annotations

import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import anyio
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from .models import (
    MAX_MCP_DISCOVERED_TOOLS,
    MCPConfigurationError,
    MCPProfile,
    MCPToolDescriptor,
    MCPTransport,
)
from .store import MCPConfigStore


class MCPDiscoveryError(RuntimeError):
    pass


class MCPDiscoveryTimeout(MCPDiscoveryError):
    pass


class MCPMissingEnvironment(MCPDiscoveryError):
    pass


class MCPStdioDiscoveryClient:
    """Opens one bounded discovery session and always closes the subprocess.

    The first slice is intentionally ephemeral: `ready` means the profile was
    successfully discovered, not that UV Studio keeps a child process resident.
    Tool execution is a later permission boundary.
    """

    def __init__(self, config_store: MCPConfigStore) -> None:
        self.config_store = config_store

    async def discover(self, profile: MCPProfile) -> tuple[MCPToolDescriptor, ...]:
        if profile.transport is not MCPTransport.STDIO:
            raise MCPDiscoveryError(f"unsupported MCP transport: {profile.transport.value}")
        env = self._resolve_environment(profile)
        cwd = self._resolve_cwd(profile)
        params = StdioServerParameters(
            command=profile.command,
            args=list(profile.args),
            env=env,
            cwd=cwd,
        )

        log_path = self.config_store.stderr_log_path(profile.profile_id)
        stack = AsyncExitStack()
        log_handle = log_path.open("w", encoding="utf-8", errors="replace")
        try:
            try:
                # AnyIO cancel scopes must be entered/exited in the same task.
                # `asyncio.wait_for()` would move the awaitable into another task
                # and breaks the official SDK's task-group cleanup contract.
                with anyio.fail_after(profile.startup_timeout_sec):
                    client = await stack.enter_async_context(
                        Client(stdio_client(params, errlog=log_handle))
                    )
            except TimeoutError as exc:
                raise MCPDiscoveryTimeout(
                    f"MCP profile {profile.profile_id!r} timed out while starting"
                ) from exc
            except Exception as exc:
                raise MCPDiscoveryError(
                    f"MCP profile {profile.profile_id!r} could not start ({type(exc).__name__})"
                ) from exc

            try:
                with anyio.fail_after(profile.discovery_timeout_sec):
                    result = await client.list_tools()
            except TimeoutError as exc:
                raise MCPDiscoveryTimeout(
                    f"MCP profile {profile.profile_id!r} timed out while listing tools"
                ) from exc
            except Exception as exc:
                raise MCPDiscoveryError(
                    f"MCP profile {profile.profile_id!r} tool discovery failed ({type(exc).__name__})"
                ) from exc

            raw_tools = list(result.tools)
            if len(raw_tools) > MAX_MCP_DISCOVERED_TOOLS:
                raise MCPDiscoveryError(
                    f"MCP profile exposed more than {MAX_MCP_DISCOVERED_TOOLS} tools"
                )
            descriptors = tuple(self._normalize_tool(tool) for tool in raw_tools)
            names = [tool.name for tool in descriptors]
            if len(set(names)) != len(names):
                raise MCPDiscoveryError("MCP server returned duplicate tool names")
            return descriptors
        finally:
            try:
                await stack.aclose()
            finally:
                log_handle.close()

    @staticmethod
    def _resolve_environment(profile: MCPProfile) -> dict[str, str]:
        child_env: dict[str, str] = {}
        missing: list[str] = []
        for child_name, source_name in profile.env_refs:
            value = os.environ.get(source_name)
            if value is None:
                missing.append(source_name)
            else:
                child_env[child_name] = value
        if missing:
            raise MCPMissingEnvironment(
                "missing required host environment variables: " + ", ".join(sorted(missing))
            )
        return child_env

    @staticmethod
    def _resolve_cwd(profile: MCPProfile) -> str | None:
        if profile.cwd is None:
            return None
        path = Path(profile.cwd).expanduser().resolve()
        if not path.is_dir():
            raise MCPConfigurationError(
                f"MCP working directory does not exist or is not a directory: {profile.cwd!r}"
            )
        return str(path)

    @staticmethod
    def _normalize_tool(tool: Any) -> MCPToolDescriptor:
        input_schema = getattr(tool, "input_schema", None)
        if input_schema is None:
            input_schema = getattr(tool, "inputSchema", None)
        output_schema = getattr(tool, "output_schema", None)
        if output_schema is None:
            output_schema = getattr(tool, "outputSchema", None)
        title = getattr(tool, "title", None) or None
        description = getattr(tool, "description", None) or None
        return MCPToolDescriptor(
            name=getattr(tool, "name", None),
            title=title,
            description=description,
            input_schema=input_schema or {},
            output_schema=output_schema,
        )
