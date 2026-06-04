# Claude A Completion Report

Status: **DONE**

## Summary

Implemented TASK-115: Capability router scaffold v1 — a minimal read-only capability routing module that inspects user goals and plugin manifest metadata to return candidate capabilities, risk levels, required confirmations, and expected deliverables.

## PM Review Fixes Applied

1. **Secret-like version redaction**: `version` field in `CandidatePlugin` now uses `_safe_str()` to redact secret-like values (e.g., `sk-PM-SECRET-VERSION-XYZ`). Both direct and registry outputs are safe.
2. **Malformed outer JSON error**: `route_capability_request_json()` now returns bounded safe error (`"plugin_manifest_jsons: invalid JSON or not a list"`) instead of silently treating malformed JSON as empty list.
3. **Tests added**: `test_secret_version_not_leaked`, `test_malformed_outer_json_returns_error`, `test_malformed_outer_json_not_a_list_returns_error`, `test_registry_tool_permission_exact`, `test_no_durable_state_mutation`.

## Changes

### New file: `mini_agent/capability_router.py`
- Pure read-only routing logic: no plugin loading, no execution, no state mutation
- `route_capability_request(goal, plugin_manifest_jsons, max_candidates)` — main routing function
- `route_capability_request_json(...)` — JSON string wrapper with bounded error handling
- Keyword extraction with underscore/hyphen splitting for compound names
- Risk inference: aggregates tool risks (destructive/external_send → high, write → medium, read → low)
- Deterministic output: sorted candidates by score then name
- Secret-like plugin names AND versions redacted via `_safe_str` from plugins.py
- `max_candidates` clamped to [1, 20]

### Edited: `mini_agent/toolkits/registry_builder.py` (minimal edit)
- Registered `route_capability_request` tool with `ToolPermission(category="local", risk="read")`
- Only the final `return registry` block was modified

### Edited: `tests/test_plugins.py`
- 25 tests total for capability router (20 original + 5 from PM review fix)

## Verification

```
python3 -m unittest tests.test_plugins tests.test_mini_agent  → 201 tests OK
python3 evals/run_evals.py                                    → 436 passed, 0 failed
git diff --check                                              → (clean)
```

## Notes

- Worktree clean before starting; no conflicts detected.
- `registry_builder.py` edit is minimal; Claude B's TASK-116 should not conflict.
- No commit or push performed.
