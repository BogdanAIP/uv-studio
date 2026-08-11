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
        ]
    )


def write_exit_marker() -> None:
    marker = os.environ.get("UV_MCP_FIXTURE_EXIT_FILE")
    if marker:
        Path(marker).write_text("stopped\n", encoding="utf-8")


async def run_server() -> None:
    app = Server("uv-studio-mcp-test", on_list_tools=handle_list_tools)
    try:
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    finally:
        write_exit_marker()


if __name__ == "__main__":
    anyio.run(run_server)
