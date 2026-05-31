# Claude B Completion Report - TASK-041

Status: completed, ready for Codex review

## Summary

Added deterministic offline eval coverage for Nora MCP server adapter (TASK-040).

Five new eval cases added to `evals/run_evals.py`:

1. **mcp_optional_dependency** — MCP module is importable without `mcp` package. `create_server` raises `ImportError` with clear install guidance when `mcp` is missing.

2. **mcp_tool_export_basics** — Allowed tools appear in MCP metadata with stable names, descriptions, and input schemas. Metadata is JSON-serializable. Specific tools (calculate) verified.

3. **mcp_safety_allowlist** — High-risk tools (run_shell_command, write_file, git_commit, etc.) not in default allowlist and not in exported metadata. Disallowed tool calls return JSON error with "未在允许列表中". Output is bounded.

4. **mcp_compatibility** — Existing OpenAI-style tool metadata still works. MCP metadata works alongside. Memory tools (save_memory, search_memory) work through adapter. Memory record tools work through adapter.

5. **mcp_failure_isolation** — Unknown tool returns "未知工具" error. Missing required args returns error. Handler errors return "工具调用失败" error. Handler exception with secret sentinel does not leak into MCP output. All errors are JSON-serializable. Registry still works after errors.

## Safety Assertions

- High-risk tools excluded from default allowlist and MCP metadata
- Disallowed calls return JSON errors, not exceptions
- Output bounded via truncation
- No external API calls or mcp package required

## Diff

```text
 evals/run_evals.py | 209 ++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 209 insertions(+)
```

## Tests

```text
python3 evals/run_evals.py
168 passed, 0 failed

python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
Ran 159 tests in 3.405s
OK

git diff --check
(clean)
```

## Notes

- No runtime code changed — eval only as instructed.
- TASK-040 implementation was already complete.
- No commit or push performed.
- Known limitations: none.
