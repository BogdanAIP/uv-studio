"""Bounded read-only MCP stdio discovery using the official Python SDK v2."""

from __future__ import annotations

import os
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
    """Open one bounded discovery session and always close the subprocess.

    `ready` means the latest bounded discovery succeeded; UV Studio does not keep
    a hidden MCP child process resident after this method returns.
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
        log_handle = log_path.open("w", encoding="utf-8", errors="replace")
        session_timeout = profile.startup_timeout_sec + profile.discovery_timeout_sec
        try:
            try:
                # The MCP SDK keeps AnyIO task-group/cancel scopes open for the
                # full Client context lifetime. Therefore the outer timeout must
                # remain open until Client.__aexit__ completes (strict LIFO).
                with anyio.fail_after(session_timeout):
                    async with Client(stdio_client(params, errlog=log_handle)) as client:
                        try:
                            # This nested scope enters and exits wholly while the
                            # Client context is active, so cancel-scope ordering is
                            # valid and list_tools still has its own hard budget.
                            with anyio.fail_after(profile.discovery_timeout_sec):
                                result = await client.list_tools()
                        except TimeoutError as exc:
                            raise MCPDiscoveryTimeout(
                                f"MCP profile {profile.profile_id!r} timed out while listing tools"
                            ) from exc
                        except MCPDiscoveryTimeout:
                            raise
                        except Exception as exc:
                            raise MCPDiscoveryError(
                                f"MCP profile {profile.profile_id!r} tool discovery failed "
                                f"({type(exc).__name__})"
                            ) from exc
            except MCPDiscoveryTimeout:
                raise
            except TimeoutError as exc:
                raise MCPDiscoveryTimeout(
                    f"MCP profile {profile.profile_id!r} discovery session timed out"
                ) from exc
            except Exception as exc:
                raise MCPDiscoveryError(
                    f"MCP profile {profile.profile_id!r} could not complete discovery "
                    f"({type(exc).__name__})"
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
