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

## Design notes

- **Server-side only (v1):** This adapter runs Nora as an MCP *server*.
  There is no MCP client that would let Nora call external MCP tools.
- **No code duplication:** Tools are dispatched through `ToolRegistry.call()`,
  which preserves all existing confirmation and permission logic.
- **Output bounding:** Tool results are truncated at 4 000 characters to
  prevent oversized MCP responses.
- **Graceful degradation:** If `mcp` is not installed, the module still
  imports — only `create_server()` and `main()` raise.
