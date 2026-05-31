# Claude A Completion Report

Task: TASK-040 — Optional MCP server adapter for Nora ToolRegistry
Status: completed (review fix x2 applied)

## Summary

Added an optional MCP (Model Context Protocol) server adapter that exposes
selected `ToolRegistry` tools to MCP-capable clients over stdio transport.
The `mcp` package is an optional extra — all core logic works without it.

## Review fix 1: extract `call_mcp_tool` helper

Extracted dispatch logic from `create_server()` into a pure-Python
`call_mcp_tool()` helper. `create_server()` now delegates to it (one line).

## Review fix 2: sanitize handler errors

`call_mcp_tool()` no longer returns raw exception text for non-TypeError
handler errors. Returns a generic `{"error": "工具调用失败"}` instead,
preventing secret/token leakage through MCP responses.

Also fixed `notify_codex.sh` to stop reintroducing PM_INBOX trailing
whitespace on every run.

## Files changed

| File | Action |
|------|--------|
| `mini_agent/mcp_server.py` | new — adapter module with `call_mcp_tool` helper |
| `tests/test_mcp_server.py` | new — 25 tests (all pass without mcp) |
| `docs/knowledge/MCP_INTEGRATION.md` | new — usage & design docs |
| `pyproject.toml` | modified — optional dep + entrypoint |
| `setup.py` | modified — extras_require + entrypoint |
| `agent_tasks/notify_codex.sh` | fixed — no longer adds trailing blank line |
| `agent_tasks/PM_INBOX.md` | fixed trailing blank line at EOF |

## Verification run

```
python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
  → 159 tests OK

python3 evals/run_evals.py
  → 168 passed, 0 failed

git diff --check
  → clean
```

## Known limitations

- Server-side only (v1): no MCP client for calling external MCP tools.
- MCP SDK requires Python >= 3.10; on 3.9 the module imports but
  `create_server()` raises at runtime.
- The `mcp` package is not installed in the current test environment, so
  the MCP SDK integration path (server.run over stdio) was not live-tested.
