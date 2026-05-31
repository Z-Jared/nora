# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-040: Optional MCP server adapter for Nora ToolRegistry.

Add a narrow, optional MCP server integration so Nora can expose selected existing `ToolRegistry` tools to MCP-capable clients without changing Nora's main agent loop.

MCP Python SDK reference:
- Official SDK: https://github.com/modelcontextprotocol/python-sdk
- Docs: https://modelcontextprotocol.github.io/python-sdk/
- PyPI package: `mcp`

## Scope

Build the smallest safe server-side slice.

1. Optional dependency:
   - Add an optional extra, likely `mcp = ["mcp>=1.0"]`, not a required dependency.
   - Keep default install and all existing tests working without `mcp` installed.
   - Nora currently declares `requires-python = ">=3.9"`; verify the chosen `mcp` version is compatible. If not compatible, do not raise Nora's Python floor in this task; document the limitation and keep the import optional.

2. Adapter module:
   - Suggested module: `mini_agent/mcp_server.py` or `mini_agent/toolkits/mcp_server.py`.
   - Provide a pure-Python adapter that can:
     - Convert `ToolRegistry.to_openai_tools()` metadata into MCP tool definitions.
     - Call existing registry tools by name.
     - Return text/JSON output in a bounded way.
   - Avoid duplicating tool implementations.

3. Server entrypoint:
   - Add a CLI/script entrypoint for stdio server mode, e.g. `nora-mcp = "mini_agent.mcp_server:main"`.
   - Use the official SDK if installed.
   - If `mcp` is missing, return a clear error explaining how to install the optional extra.

4. Safety:
   - Expose a conservative allowlist by default. Suggested first allowlist:
     - `calculate`
     - `search_memory`
     - `save_memory`
     - `search_memory_records`
     - `list_memory_records`
     - `get_memory_record`
     - `save_memory_record`
   - Do not expose shell, file-write, git-write, browser-click, process-start, or other high-risk tools by default.
   - Preserve existing registry confirmation behavior for any write-capable tool that is exposed.
   - Keep outputs bounded/truncated.

5. Documentation:
   - Add a short section to README or a new `docs/knowledge/MCP_INTEGRATION.md`.
   - Explain optional install, stdio usage, default allowlist, and why this is server-side only for v1.

## Suggested Tests

Add focused tests, likely `tests/test_mcp_server.py`, that do not require `mcp` installed:

1. Tool metadata conversion preserves name, description, parameters.
2. Default allowlist excludes high-risk tools.
3. Adapter calls allowed tools through `ToolRegistry`.
4. Disallowed tool calls return JSON error, not crash.
5. Missing `mcp` dependency path returns a clear message.
6. Existing registry behavior remains unchanged.

If `mcp` is installed in the local environment, optional import smoke tests are OK, but the suite must pass without it.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
python3 evals/run_evals.py
git diff --check
```

If you touch packaging or registry builder broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
