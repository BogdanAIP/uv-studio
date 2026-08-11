"""Bounded MCP stdio discovery and exact tool invocation via official SDK v2."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import anyio
from mcp import Client, MCPError, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_types import REQUEST_TIMEOUT

from .models import (
    MAX_MCP_DISCOVERED_TOOLS,
    MCPConfigurationError,
    MCPProfile,
    MCPToolDescriptor,
    MCPTransport,
)
from .store import MCPConfigStore

_MAX_INVOCATION_ARGUMENT_BYTES = 256 * 1024
_DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024


class MCPDiscoveryError(RuntimeError):
    pass


class MCPDiscoveryTimeout(MCPDiscoveryError):
    pass


class MCPMissingEnvironment(MCPDiscoveryError):
    pass


class MCPInvocationError(RuntimeError):
    pass


class MCPInvocationTimeout(MCPInvocationError):
    pass


class MCPInvocationToolMissing(MCPInvocationError):
    pass


class MCPInvocationToolError(MCPInvocationError):
    pass


class MCPInvocationResponseTooLarge(MCPInvocationError):
    pass


class MCPStdioDiscoveryClient:
    """Open bounded ephemeral MCP sessions; never keep hidden child processes."""

    def __init__(self, config_store: MCPConfigStore) -> None:
        self.config_store = config_store

    async def discover(self, profile: MCPProfile) -> tuple[MCPToolDescriptor, ...]:
        if profile.transport is not MCPTransport.STDIO:
            raise MCPDiscoveryError(f"unsupported MCP transport: {profile.transport.value}")
        params = self._stdio_params(profile)
        log_path = self.config_store.stderr_log_path(profile.profile_id)
        log_handle = log_path.open("w", encoding="utf-8", errors="replace")
        session_timeout = profile.startup_timeout_sec + profile.discovery_timeout_sec
        result = None
        pending_error: MCPDiscoveryError | None = None
        try:
            try:
                with anyio.fail_after(session_timeout):
                    async with Client(
                        stdio_client(params, errlog=log_handle),
                        read_timeout_seconds=profile.discovery_timeout_sec,
                    ) as client:
                        try:
                            result = await client.list_tools()
                        except MCPError as exc:
                            if getattr(exc.error, "code", None) == REQUEST_TIMEOUT:
                                pending_error = MCPDiscoveryTimeout(
                                    f"MCP profile {profile.profile_id!r} timed out while listing tools"
                                )
                            else:
                                pending_error = MCPDiscoveryError(
                                    f"MCP profile {profile.profile_id!r} tool discovery failed "
                                    f"(MCPError code={getattr(exc.error, 'code', 'unknown')})"
                                )
                        except Exception as exc:
                            pending_error = MCPDiscoveryError(
                                f"MCP profile {profile.profile_id!r} tool discovery failed "
                                f"({type(exc).__name__})"
                            )
            except TimeoutError as exc:
                raise MCPDiscoveryTimeout(
                    f"MCP profile {profile.profile_id!r} discovery session timed out"
                ) from exc
            except MCPDiscoveryError:
                raise
            except Exception as exc:
                raise MCPDiscoveryError(
                    f"MCP profile {profile.profile_id!r} could not complete discovery "
                    f"({type(exc).__name__})"
                ) from exc

            if pending_error is not None:
                raise pending_error
            if result is None:
                raise MCPDiscoveryError(
                    f"MCP profile {profile.profile_id!r} completed without a tool-list result"
                )
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

    async def invoke(
        self,
        profile: MCPProfile,
        *,
        tool_name: str,
        arguments: Mapping[str, Any],
        timeout_sec: float = 30.0,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
    ) -> dict[str, Any]:
        """Invoke one exact tool after verifying it is still reported by the server.

        The process is ephemeral: initialize -> list_tools -> exact-name check ->
        call_tool -> SDK cleanup. UV Studio errors are raised only after the SDK
        context exits so AnyIO task groups and subprocess trees unwind normally.
        """

        if profile.transport is not MCPTransport.STDIO:
            raise MCPInvocationError(f"unsupported MCP transport: {profile.transport.value}")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise MCPInvocationError("tool_name must be a non-empty string")
        if not isinstance(arguments, Mapping):
            raise MCPInvocationError("MCP tool arguments must be an object")
        if timeout_sec < 0.1 or timeout_sec > 300:
            raise MCPInvocationError("MCP invocation timeout must be between 0.1 and 300 seconds")
        if max_response_bytes < 1024 or max_response_bytes > 16 * 1024 * 1024:
            raise MCPInvocationError("invalid MCP response size limit")

        try:
            arg_bytes = json.dumps(
                dict(arguments),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise MCPInvocationError("MCP arguments must be JSON serializable") from exc
        if len(arg_bytes) > _MAX_INVOCATION_ARGUMENT_BYTES:
            raise MCPInvocationError(
                f"MCP invocation arguments exceed {_MAX_INVOCATION_ARGUMENT_BYTES} bytes"
            )

        params = self._stdio_params(profile)
        log_path = self.config_store.stderr_log_path(profile.profile_id)
        log_handle = log_path.open("w", encoding="utf-8", errors="replace")
        session_timeout = profile.startup_timeout_sec + timeout_sec * 2
        result = None
        pending_error: MCPInvocationError | None = None
        try:
            try:
                with anyio.fail_after(session_timeout):
                    async with Client(
                        stdio_client(params, errlog=log_handle),
                        read_timeout_seconds=timeout_sec,
                    ) as client:
                        try:
                            tools_result = await client.list_tools()
                            tool_names = {tool.name for tool in tools_result.tools}
                            if tool_name not in tool_names:
                                pending_error = MCPInvocationToolMissing(
                                    f"MCP tool {tool_name!r} is no longer reported by profile "
                                    f"{profile.profile_id!r}"
                                )
                            else:
                                result = await client.call_tool(tool_name, dict(arguments))
                        except MCPError as exc:
                            if getattr(exc.error, "code", None) == REQUEST_TIMEOUT:
                                pending_error = MCPInvocationTimeout(
                                    f"MCP tool {tool_name!r} timed out"
                                )
                            else:
                                pending_error = MCPInvocationError(
                                    f"MCP tool {tool_name!r} failed "
                                    f"(MCPError code={getattr(exc.error, 'code', 'unknown')})"
                                )
                        except Exception as exc:
                            pending_error = MCPInvocationError(
                                f"MCP tool {tool_name!r} failed ({type(exc).__name__})"
                            )
            except TimeoutError as exc:
                raise MCPInvocationTimeout(
                    f"MCP profile {profile.profile_id!r} invocation session timed out"
                ) from exc
            except MCPInvocationError:
                raise
            except Exception as exc:
                raise MCPInvocationError(
                    f"MCP profile {profile.profile_id!r} could not complete invocation "
                    f"({type(exc).__name__})"
                ) from exc

            if pending_error is not None:
                raise pending_error
            if result is None:
                raise MCPInvocationError("MCP invocation completed without a result")

            payload = result.model_dump(mode="json", by_alias=True, exclude_none=True)
            try:
                encoded = json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise MCPInvocationError("MCP result was not JSON serializable") from exc
            if len(encoded) > max_response_bytes:
                raise MCPInvocationResponseTooLarge(
                    f"MCP result exceeds {max_response_bytes} bytes"
                )
            if bool(payload.get("isError", payload.get("is_error", False))):
                raise MCPInvocationToolError(
                    f"MCP tool {tool_name!r} returned an error result"
                )
            return payload
        finally:
            log_handle.close()

    def _stdio_params(self, profile: MCPProfile) -> StdioServerParameters:
        env = self._resolve_environment(profile)
        cwd = self._resolve_cwd(profile)
        return StdioServerParameters(
            command=profile.command,
            args=list(profile.args),
            env=env,
            cwd=cwd,
        )

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
