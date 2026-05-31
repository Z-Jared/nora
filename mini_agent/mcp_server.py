"""Optional MCP (Model Context Protocol) server adapter for Nora ToolRegistry.

Exposes selected registry tools to MCP-capable clients via stdio transport.
The ``mcp`` package is an optional dependency — all core logic works without it;
only ``create_server`` and ``main`` require the SDK installed.

Install with:  pip install nora-local-ai[mcp]

Python note: the ``mcp`` SDK requires Python >= 3.10.  Nora's floor is 3.9,
so this module is importable on 3.9 but ``create_server`` will raise at
runtime if the SDK or Python version is too old.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

from mini_agent.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Default safe allowlist
# ---------------------------------------------------------------------------

DEFAULT_ALLOWLIST: frozenset[str] = frozenset({
    "calculate",
    "search_memory",
    "save_memory",
    "search_memory_records",
    "list_memory_records",
    "get_memory_record",
    "save_memory_record",
})

MAX_OUTPUT_CHARS = 4000

# ---------------------------------------------------------------------------
# Pure-Python helpers (no mcp dependency)
# ---------------------------------------------------------------------------


def registry_to_mcp_tools(
    registry: ToolRegistry,
    allowlist: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    """Convert ``registry`` tool metadata to MCP ``Tool`` dicts.

    Returns a list of dicts with keys ``name``, ``description``, ``inputSchema``
    matching the shape ``mcp.types.Tool`` expects.  No ``mcp`` import needed.
    """
    effective = allowlist if allowlist is not None else DEFAULT_ALLOWLIST
    tools: list[dict[str, Any]] = []
    for entry in registry.to_openai_tools():
        fn = entry["function"]
        if fn["name"] not in effective:
            continue
        tools.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "inputSchema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return tools


def is_tool_allowed(name: str, allowlist: Optional[set[str]] = None) -> bool:
    effective = allowlist if allowlist is not None else DEFAULT_ALLOWLIST
    return name in effective


def _truncate(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n…[truncated, {len(text)} chars total]"


def call_mcp_tool(
    registry: ToolRegistry,
    name: str,
    arguments: dict[str, Any],
    allowlist: Optional[set[str]] = None,
) -> str:
    """Dispatch a tool call through the allowlist and *registry*.

    Pure-Python helper with no ``mcp`` dependency.  Handles allowlist
    rejection, unknown tools, malformed arguments, handler errors, and
    output truncation.  Returns a JSON string on error or the truncated
    tool result on success.
    """
    if not is_tool_allowed(name, allowlist):
        return json.dumps({"error": f"工具未在允许列表中: {name}"}, ensure_ascii=False)
    try:
        result = registry.call(name, **arguments)
    except KeyError:
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
    except TypeError as exc:
        return json.dumps({"error": f"参数错误: {exc}"}, ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "工具调用失败"}, ensure_ascii=False)
    return _truncate(result)


# ---------------------------------------------------------------------------
# MCP server factory (requires ``mcp`` package)
# ---------------------------------------------------------------------------


def create_server(
    registry: ToolRegistry,
    allowlist: Optional[set[str]] = None,
    server_name: str = "nora",
    server_version: str = "0.1.0",
):
    """Create and return an MCP ``Server`` backed by *registry*.

    Raises ``ImportError`` if the ``mcp`` package is not installed or if the
    running Python is older than 3.10.
    """
    try:
        import mcp.server.stdio  # noqa: F401
        import mcp.types as types
        from mcp.server.lowlevel import NotificationOptions, Server
        from mcp.server.models import InitializationOptions
    except ImportError as exc:
        raise ImportError(
            "mcp 包未安装。请运行: pip install nora-local-ai[mcp]\n"
            "注意: MCP SDK 需要 Python >= 3.10。"
        ) from exc

    mcp_tools_meta = registry_to_mcp_tools(registry, allowlist)

    server = Server(server_name)

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in mcp_tools_meta
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=call_mcp_tool(registry, name, arguments, allowlist))]

    init_options = InitializationOptions(
        server_name=server_name,
        server_version=server_version,
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    return server, init_options


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


async def _async_main(
    registry: Optional[ToolRegistry] = None,
    allowlist: Optional[set[str]] = None,
) -> None:
    try:
        import mcp.server.stdio
    except ImportError:
        print(
            "错误: mcp 包未安装。请运行: pip install nora-local-ai[mcp]\n"
            "注意: MCP SDK 需要 Python >= 3.10。",
            file=sys.stderr,
        )
        sys.exit(1)

    if registry is None:
        from mini_agent.toolkits import build_default_registry
        registry = build_default_registry()

    server, init_options = create_server(registry, allowlist)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)


def main(
    registry: Optional[ToolRegistry] = None,
    allowlist: Optional[set[str]] = None,
) -> None:
    """CLI entrypoint for ``nora-mcp``.  Starts a stdio MCP server."""
    import asyncio
    asyncio.run(_async_main(registry=registry, allowlist=allowlist))


if __name__ == "__main__":
    main()
