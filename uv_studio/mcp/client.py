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

MAX_MCP_CALL_REQUEST_BYTES = 1 * 1024 * 1024
MAX_MCP_CALL_RESPONSE_BYTES = 4 * 1024 * 1024


class MCPDiscoveryError(RuntimeError):
    pass


class MCPDiscoveryTimeout(MCPDiscoveryError):
    pass


class MCPMissingEnvironment(MCPDiscoveryError):
    pass


class MCPCallError(RuntimeError):
    code = "mcp_call_failed"


class MCPCallTimeout(MCPCallError):
    code = "mcp_call_timeout"


class MCPToolReturnedError(MCPCallError):
    code = "mcp_tool_error"


class MCPRequestTooLarge(MCPCallError):
    code = "mcp_request_too_large"


class MCPResponseTooLarge(MCPCallError):
    code = "mcp_response_too_large"


class MCPStdioDiscoveryClient:
    """Open one bounded MCP session and always close the subprocess.

    Discovery and invocation deliberately use short-lived sessions. A READY
    discovery snapshot never means a hidden child process remains resident.
    """

    def __init__(self, config_store: MCPConfigStore) -> None:
        self.config_store = config_store

    async def discover(self, profile: MCPProfile) -> tuple[MCPToolDescriptor, ...]:
        if profile.transport is not MCPTransport.STDIO:
            raise MCPDiscoveryError(f"unsupported MCP transport: {profile.transport.value}")
        env = self._resolve_environment(profile)
        cwd = self._resolve_cwd(profile)
        params = self._stdio_parameters(profile, env=env, cwd=cwd)

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

    async def call_tool(
        self,
        profile: MCPProfile,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Invoke one exact tool name in a bounded short-lived stdio session."""
        if profile.transport is not MCPTransport.STDIO:
            raise MCPCallError(f"unsupported MCP transport: {profile.transport.value}")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise MCPCallError("MCP tool name must be non-empty")
        normalized_arguments = self._normalize_call_arguments(arguments)
        self._enforce_request_limit(tool_name, normalized_arguments)

        env = self._resolve_environment_for_call(profile)
        cwd = self._resolve_cwd_for_call(profile)
        params = self._stdio_parameters(profile, env=env, cwd=cwd)
        log_path = self.config_store.stderr_log_path(profile.profile_id)
        log_handle = log_path.open("w", encoding="utf-8", errors="replace")
        session_timeout = profile.startup_timeout_sec + profile.discovery_timeout_sec
        result: Any = None
        pending_error: MCPCallError | None = None
        try:
            try:
                with anyio.fail_after(session_timeout):
                    async with Client(
                        stdio_client(params, errlog=log_handle),
                        read_timeout_seconds=profile.discovery_timeout_sec,
                    ) as client:
                        try:
                            result = await client.call_tool(
                                tool_name,
                                normalized_arguments,
                                read_timeout_seconds=profile.discovery_timeout_sec,
                            )
                        except MCPError as exc:
                            if getattr(exc.error, "code", None) == REQUEST_TIMEOUT:
                                pending_error = MCPCallTimeout(
                                    f"MCP profile {profile.profile_id!r} timed out while calling bound tool"
                                )
                            else:
                                pending_error = MCPCallError(
                                    f"MCP profile {profile.profile_id!r} tool call failed at protocol level"
                                )
                        except Exception as exc:
                            pending_error = MCPCallError(
                                f"MCP profile {profile.profile_id!r} tool call failed "
                                f"({type(exc).__name__})"
                            )
            except TimeoutError as exc:
                raise MCPCallTimeout(
                    f"MCP profile {profile.profile_id!r} invocation session timed out"
                ) from exc
            except MCPCallError:
                raise
            except Exception as exc:
                raise MCPCallError(
                    f"MCP profile {profile.profile_id!r} could not complete tool invocation "
                    f"({type(exc).__name__})"
                ) from exc

            if pending_error is not None:
                raise pending_error
            if result is None:
                raise MCPCallError(
                    f"MCP profile {profile.profile_id!r} completed without a tool-call result"
                )

            normalized = self._normalize_call_result(result)
            self._enforce_response_limit(normalized)
            if bool(getattr(result, "is_error", False)):
                raise MCPToolReturnedError(
                    f"MCP profile {profile.profile_id!r} bound tool returned an error"
                )
            return normalized
        finally:
            log_handle.close()

    @staticmethod
    def _stdio_parameters(
        profile: MCPProfile,
        *,
        env: dict[str, str],
        cwd: str | None,
    ) -> StdioServerParameters:
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

    @classmethod
    def _resolve_environment_for_call(cls, profile: MCPProfile) -> dict[str, str]:
        try:
            return cls._resolve_environment(profile)
        except MCPMissingEnvironment as exc:
            raise MCPCallError(str(exc)) from exc

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

    @classmethod
    def _resolve_cwd_for_call(cls, profile: MCPProfile) -> str | None:
        try:
            return cls._resolve_cwd(profile)
        except MCPConfigurationError as exc:
            raise MCPCallError(str(exc)) from exc

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

    @staticmethod
    def _normalize_call_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            raise MCPCallError("MCP tool arguments must be a JSON object")
        normalized = dict(arguments)
        try:
            json.dumps(
                normalized,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise MCPCallError("MCP tool arguments must contain finite JSON data") from exc
        return normalized

    @staticmethod
    def _normalize_call_result(result: Any) -> dict[str, Any]:
        model_dump = getattr(result, "model_dump", None)
        if not callable(model_dump):
            raise MCPCallError("MCP SDK returned an unsupported tool-call result type")
        try:
            normalized = model_dump(mode="json", by_alias=True, exclude_none=True)
        except Exception as exc:
            raise MCPCallError("MCP SDK result could not be normalized safely") from exc
        if not isinstance(normalized, dict):
            raise MCPCallError("MCP SDK returned a non-object tool-call result")
        return normalized

    @staticmethod
    def _enforce_request_limit(tool_name: str, arguments: dict[str, Any]) -> None:
        encoded = json.dumps(
            {"tool_name": tool_name, "arguments": arguments},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > MAX_MCP_CALL_REQUEST_BYTES:
            raise MCPRequestTooLarge(
                f"MCP tool request exceeds {MAX_MCP_CALL_REQUEST_BYTES} bytes"
            )

    @staticmethod
    def _enforce_response_limit(result: dict[str, Any]) -> None:
        try:
            encoded = json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise MCPCallError("MCP tool result is not finite JSON data") from exc
        if len(encoded) > MAX_MCP_CALL_RESPONSE_BYTES:
            raise MCPResponseTooLarge(
                f"MCP tool response exceeds {MAX_MCP_CALL_RESPONSE_BYTES} bytes"
            )
