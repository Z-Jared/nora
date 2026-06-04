# Claude B Completion Report

Status: ready for Codex review

## Summary

TASK-112: Deterministic eval coverage for MCP adapter safe tool surface v1.

Added deterministic offline eval coverage for the MCP adapter's safe tool surface.

## Changes

- `evals/run_evals.py`
  - Added MCP helper imports.
  - Added 8 deterministic evals:
    - `mcp_default_allowlist_boundaries`
    - `mcp_permission_surface_inspection`
    - `mcp_custom_allowlist_boundaries`
    - `mcp_custom_allowlist_unsafe_guard`
    - `mcp_registry_permission_boundaries`
    - `mcp_safe_json_errors_no_leak`
    - `mcp_bounded_output_truncation`
    - `mcp_memory_tool_compatibility`

## Coverage

- Default allowlist includes safe tools and excludes high-risk tools.
- Custom allowlists are deterministic and can be empty or scoped.
- Permission surface inspection exposes safe metadata for both exposed and hidden/blocked tools.
- Unsafe custom allowlist tools are hidden/blocked by default and require explicit opt-in.
- Registered tools outside the allowlist are rejected with safe JSON errors.
- Handler exceptions, unknown tools, malformed args, and disallowed tools do not leak secret sentinels.
- Long output remains bounded and short output remains unchanged.
- Memory and calculate tools still work through `call_mcp_tool`.

## Tests

```text
python3 evals/run_evals.py
423 passed, 0 failed

python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
Ran 182 tests in 7.844s — OK

git diff --check
clean
```

## Notes

- No runtime behavior changes were made by Claude B.
- PM integrated the evals onto current `main` without removing TASK-110 eval coverage.
- PM added one eval for `inspect_mcp_tool_surface(...)` after review found the inspection requirement needed coverage for unexposed tools.
- No push performed.
