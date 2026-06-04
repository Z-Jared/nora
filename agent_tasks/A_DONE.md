# Claude A Completion Report

Status: ready for Codex review

## Summary

TASK-111: MCP adapter permission-aware tool surface hardening v1.

Hardened the MCP adapter with permission metadata exposure, custom-allowlist validation, and MCP boundary blocking for unsafe tools.

## Changes

- `mini_agent/mcp_server.py`
  - Added permission metadata to MCP tool listings: `category`, `risk`, `requires_confirmation`, and `exposed`.
  - Added `inspect_mcp_tool_surface(...)` for full safe MCP surface inspection, including hidden/blocked tools.
  - Added `validate_allowlist(...)` for auditing custom MCP allowlists.
  - Added MCP permission guard for unsafe tools.
  - Added explicit `allow_unsafe_tools=True` opt-in for trusted local deployments.
  - Preserved optional `mcp` dependency behavior and output truncation.
- `tests/test_mcp_server.py`
  - Added coverage for permission metadata, unsafe custom allowlist filtering, confirmation-required blocking, non-memory write blocking, and explicit unsafe opt-in.
- `docs/knowledge/MCP_INTEGRATION.md`
  - Documented permission metadata, custom allowlist guardrails, and unsafe opt-in.

## Tests

```text
python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
Ran 182 tests in 7.844s — OK

python3 evals/run_evals.py
423 passed, 0 failed

git diff --check
clean
```

## Notes

- No push performed.
- No edits to B files, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- PM review fix strengthened the worker implementation so unsafe non-memory write tools, such as `register_worker`, are blocked by default and require explicit `allow_unsafe_tools=True`.
- PM review fix also added `inspect_mcp_tool_surface(...)`, because `registry_to_mcp_tools(...)` should only return exposed MCP tools while PM/client inspection needs safe metadata for hidden and blocked tools too.
