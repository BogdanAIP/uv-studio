from __future__ import annotations

import json
import os
from pathlib import Path

import anyio
import mcp.types as types
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server


async def handle_list_tools(
    ctx: ServerRequestContext,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    delay = float(os.environ.get("UV_MCP_FIXTURE_LIST_DELAY", "0") or "0")
    if delay:
        await anyio.sleep(delay)
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="echo_metadata",
                title="Echo Metadata",
                description="Returns deterministic test metadata.",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                },
            ),
            types.Tool(
                name="cloud_generate",
                title="Cloud Generate",
                description="Fixture representing a remote paid-capable operation.",
                input_schema={
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}},
                },
            ),
            types.Tool(
                name="slow_echo",
                title="Slow Echo",
                description="Delays before returning deterministic metadata.",
                input_schema={"type": "object"},
            ),
            types.Tool(
                name="fail_tool",
                title="Fail Tool",
                description="Returns an MCP tool error for tests.",
                input_schema={"type": "object"},
            ),
            types.Tool(
                name="oversized_response",
                title="Oversized Response",
                description="Returns a response beyond the UV Studio response limit.",
                input_schema={"type": "object"},
            ),
        ]
    )


async def handle_call_tool(
    ctx: ServerRequestContext,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    arguments = params.arguments or {}
    if params.name in {"echo_metadata", "cloud_generate"}:
        text = json.dumps(
            {"tool": params.name, "arguments": arguments},
            ensure_ascii=False,
            sort_keys=True,
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)]
        )
    if params.name == "slow_echo":
        delay = float(os.environ.get("UV_MCP_FIXTURE_CALL_DELAY", "2") or "2")
        await anyio.sleep(delay)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="slow-ok")]
        )
    if params.name == "fail_tool":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="fixture failure")],
            is_error=True,
        )
    if params.name == "oversized_response":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="x" * (5 * 1024 * 1024))]
        )
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="unknown fixture tool")],
        is_error=True,
    )


def write_exit_marker() -> None:
    marker = os.environ.get("UV_MCP_FIXTURE_EXIT_FILE")
    if marker:
        Path(marker).write_text("stopped\n", encoding="utf-8")


async def run_server() -> None:
    app = Server(
        "uv-studio-mcp-test",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )
    try:
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    finally:
        write_exit_marker()


if __name__ == "__main__":
    anyio.run(run_server)
