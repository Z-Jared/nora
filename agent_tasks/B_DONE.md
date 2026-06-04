# Claude B Completion Report

Status: ready for Codex review

## Summary

Added 13 deterministic offline eval cases for TASK-114 plugin manifest inspection in `evals/run_evals.py`. All evals are offline, deterministic, and use temporary databases.

## New Eval Cases

1. **plugin_manifest_tool_permission** — Verifies `inspect_plugin_manifest` registered with `ToolPermission(category="local", risk="read")`.
2. **plugin_manifest_valid_productivity** — Valid developer/productivity manifest returns bounded safe metadata with correct fields.
3. **plugin_manifest_malformed_json** — Malformed JSON returns safe bounded error, never raises.
4. **plugin_manifest_non_object** — Non-object JSON returns safe bounded error.
5. **plugin_manifest_malformed_tools** — Malformed tool entries (non-objects, empty names) return bounded errors; valid tools still parsed.
6. **plugin_manifest_duplicate_tool_names** — Duplicate tool names are rejected with clear error.
7. **plugin_manifest_high_risk_no_confirm** — High-risk/destructive/external-send without confirmation is rejected.
8. **plugin_manifest_high_risk_with_confirm** — High-risk/destructive/external-send with confirmation is accepted.
9. **plugin_manifest_unknown_enums** — Unknown enum values for auth, permission_category, risk, data_sensitivity, event_log are normalized to safe defaults; raw values not echoed.
10. **plugin_manifest_secret_redaction** — Secret-like values in tool names/domains/capabilities are redacted or omitted.
11. **plugin_manifest_read_only_no_mutation** — Inspection is read-only: no durable task/worker/event mutation (includes worker store check).
12. **plugin_manifest_no_plugin_execution** — Inspection does not execute plugin code or register plugin tools: writes a marker-producing plugin file, inspects a matching manifest, asserts marker file absent and tool not registered.
13. **plugin_manifest_compatibility** — Existing MCP evals and `list_tool_permissions` still work after plugin manifest inspection.

## Diff

```text
 evals/run_evals.py | 278 ++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 278 insertions(+)
```

## Tests

```text
python3 evals/run_evals.py — 436 passed, 0 failed
python3 -m unittest tests.test_plugins tests.test_mcp_server tests.test_mini_agent — 225 tests, OK
git diff --check — clean
```

## Notes

- No push performed.
- No runtime behavior changes.
- PM review fix: added worker store snapshot to read-only eval; added dedicated no-plugin-execution eval with side-effect marker assertion.
