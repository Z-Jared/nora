# MCP Integration

Nora exposes a subset of its `ToolRegistry` tools via the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) so that
MCP-capable clients (IDE extensions, other agents, etc.) can call Nora tools
over a standard protocol.

## Install

MCP support is an **optional** extra.  Nora's core install does not pull it in.

```bash
pip install nora-local-ai[mcp]
```

The `mcp` SDK requires **Python >= 3.10**.  Nora's floor is 3.9, so:

- On Python 3.9 the module is importable but `create_server()` raises
  `ImportError` at runtime.
- On Python 3.10+ everything works after installing the extra.

## Usage

Start a stdio MCP server that exposes the default safe allowlist:

```bash
nora-mcp
```

Or from Python:

```python
from mini_agent.mcp_server import main
main()
```

The server communicates over **stdio** (stdin/stdout) using the MCP protocol.
Point your MCP client at the `nora-mcp` command.

### Custom allowlist

```python
from mini_agent.mcp_server import create_server
from mini_agent.toolkits import build_default_registry

registry = build_default_registry()
server, init_options = create_server(
    registry,
    allowlist={"calculate", "search_memory"},
)
```

Custom allowlists are still filtered through Nora's MCP permission guard.
Unsafe write/execute/interact/delete tools are not listed or callable unless
you explicitly pass `allow_unsafe_tools=True`.

Use `validate_allowlist` to inspect a custom allowlist before starting the
server:

```python
from mini_agent.mcp_server import validate_allowlist

issues = validate_allowlist(registry, {"calculate", "run_shell_command"})
# issues["high_risk"] == ["run_shell_command"]
# issues["confirmation_required"] == ["run_shell_command"]
```

Use `inspect_mcp_tool_surface` when a client or PM process needs the full safe
surface, including tools hidden by the effective allowlist or MCP permission
guard:

```python
from mini_agent.mcp_server import inspect_mcp_tool_surface

surface = inspect_mcp_tool_surface(registry)
# Each item contains name, description, inputSchema, category, risk,
# requires_confirmation, exposed, and optionally block_reason.
```

Explicit unsafe opt-in is available for trusted local deployments:

```python
server, init_options = create_server(
    registry,
    allowlist={"register_worker"},
    allow_unsafe_tools=True,
)
```

## Default allowlist

Only read-only and low-risk tools are exposed by default:

| Tool                     | Description                      |
|--------------------------|----------------------------------|
| `calculate`              | Evaluate a math expression       |
| `search_memory`          | Search memory entries            |
| `save_memory`            | Save a memory entry              |
| `search_memory_records`  | Search structured memory records |
| `list_memory_records`    | List memory records              |
| `get_memory_record`      | Get a single memory record       |
| `save_memory_record`     | Save a structured memory record  |

The following are **not** exposed by default:

- `run_shell_command` — arbitrary shell execution
- `write_file`, `replace_in_file` — filesystem writes
- `git_commit`, `git_push` — version control mutations
- `browser_click` — browser automation
- `process_start` — process management

## Permission metadata (TASK-111)

Each MCP tool now includes permission metadata in its listing:

- `category` — permission category (e.g. `general`, `memory`, `terminal`)
- `risk` — risk level (`read`, `write`, `execute`, `interact`, `delete`)
- `requires_confirmation` — whether interactive confirmation is required
- `exposed` — whether this entry is exposed by the effective allowlist and MCP permission guard

`registry_to_mcp_tools(...)` returns only exposed entries for MCP `list_tools`.
`inspect_mcp_tool_surface(...)` returns every registered tool with the same safe
bounded metadata, using `exposed=false` and `block_reason` for hidden or blocked
tools.

### Unsafe tool blocking

By default, tools are blocked at the MCP boundary when they require
confirmation, have execute/interact/delete/destructive/external-send/high risk,
or are non-memory write tools. Low-risk memory writes in the default allowlist
remain available.

Blocked call responses include a safe reason plus the tool's `category` and
`risk`; raw arguments are not echoed.

### High-risk guardrails

`validate_allowlist` flags tools that MCP would block by default. Use it to
audit custom allowlists before starting the server.

## Design notes

- **Server-side only (v1):** This adapter runs Nora as an MCP *server*.
  There is no MCP client that would let Nora call external MCP tools.
- **No code duplication:** Tools are dispatched through `ToolRegistry.call()`,
  which preserves all existing permission and event-logging logic.
- **Output bounding:** Tool results are truncated at 4 000 characters to
  prevent oversized MCP responses.
- **Graceful degradation:** If `mcp` is not installed, the module still
  imports — only `create_server()` and `main()` raise.
- **Permission guardrail:** unsafe tools are blocked at the MCP boundary by
  default; trusted local deployments must explicitly opt in with
  `allow_unsafe_tools=True`.
