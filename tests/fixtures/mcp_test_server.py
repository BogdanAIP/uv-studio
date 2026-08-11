from __future__ import annotations

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
                name="slow_tool",
                title="Slow Tool",
                description="Sleeps before returning.",
                input_schema={
                    "type": "object",
                    "properties": {"delay": {"type": "number"}},
                },
            ),
            types.Tool(
                name="error_tool",
                title="Error Tool",
                description="Returns an MCP tool error.",
                input_schema={"type": "object"},
            ),
            types.Tool(
                name="large_result",
                title="Large Result",
                description="Returns a caller-sized deterministic payload.",
                input_schema={
                    "type": "object",
                    "properties": {"size": {"type": "integer"}},
                },
            ),
        ]
    )


async def handle_call_tool(
    ctx: ServerRequestContext,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}
    if name == "echo_metadata":
        text = str(arguments.get("text", ""))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"echo:{text}")],
            structured_content={"echo": text, "kind": "fixture"},
        )
    if name == "cloud_generate":
        prompt = str(arguments.get("prompt", ""))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"generated:{prompt}")],
            structured_content={"prompt": prompt, "simulated": True},
        )
    if name == "slow_tool":
        await anyio.sleep(float(arguments.get("delay", 2.0)))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="slow-done")],
        )
    if name == "error_tool":
        return types.CallToolResult(
            is_error=True,
            content=[types.TextContent(type="text", text="fixture-error")],
        )
    if name == "large_result":
        size = max(0, min(int(arguments.get("size", 0)), 4 * 1024 * 1024))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="x" * size)],
        )
    return types.CallToolResult(
        is_error=True,
        content=[types.TextContent(type="text", text=f"unknown tool: {name}")],
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
