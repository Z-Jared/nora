# CCB Review — TASK-114: Deterministic eval coverage for plugin manifest inspection v1

**Status: APPROVED**

## Summary

13 eval cases covering plugin manifest inspection safe surface. All offline, deterministic, no runtime changes. PM review fixes (worker store snapshot, no-plugin-execution marker) properly applied.

## Coverage

| Area | Evals | Notes |
|------|-------|-------|
| Tool permission | 1 | Verifies local/read via `registry._tools` |
| Valid manifest | 1 | Bounded safe metadata, JSON-serializable |
| Malformed input | 3 | JSON errors, non-object, malformed tools — all return bounded errors |
| Duplicate tools | 1 | Rejected with clear error |
| High-risk confirmation | 2 | Without confirm rejected, with confirm accepted (destructive/external_send/high) |
| Unknown enums | 1 | All 5 enum types normalized to "unknown", raw values absent from output |
| Secret redaction | 1 | Secret-like tool names/domains/capabilities redacted/omitted |
| Read-only | 1 | Tasks/workers/events unchanged after inspection |
| No execution | 1 | Marker file absent, plugin tool not registered |
| Compatibility | 1 | MCP tools and list_tool_permissions still work |

## Key Findings

- **No runtime changes**: Only `evals/run_evals.py` modified (278 lines). No changes to `plugins.py`, `registry_builder.py`, or tests.
- **Deterministic**: All evals use `tempfile.TemporaryDirectory()` + local `NoraDB`. No network/model dependencies.
- **No-plugin-execution eval** (PM fix): Writes a side-effect plugin, inspects a manifest referencing it, asserts marker file absent and tool not registered. Strong proof that inspection is purely declarative.
- **Read-only eval** (PM fix): Snapshots task/worker/event stores before and after inspection. All counts unchanged.
- **Private attribute access**: `registry._tools.get("inspect_plugin_manifest")` is acceptable in eval context for precise permission verification. Not a runtime dependency.

## Residual Risk

None. Evals are comprehensive, deterministic, and properly isolated.
