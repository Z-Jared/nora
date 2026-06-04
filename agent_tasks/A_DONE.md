# Claude A Completion Report

Status: ready for Codex review

## Summary

TASK-113: Plugin manifest schema and inspection v1 — implemented, security fix applied.

## Changes

### `mini_agent/plugins.py` (extended)
- Added manifest v1 constants: `VALID_AUTH_METHODS`, `VALID_PERMISSION_CATEGORIES`, `VALID_RISKS`, `VALID_DATA_SENSITIVITY`, `VALID_EVENT_LOG_MODES`, `HIGH_RISK_RISKS`
- Added data models: `PluginToolMeta`, `PluginManifest`, `ManifestValidationResult`
- Added parser/validator: `parse_manifest(dict)`, `parse_manifest_json(str)`
- Validation rejects: missing identity fields, non-list tools, duplicate tool names, high-risk/external-send/destructive tools without confirmation
- Validation warns: unknown auth methods, unknown permission categories/risks/data_sensitivity/event_log modes
- Added safe inspection: `inspect_manifest(dict)`, `inspect_manifest_json(str)`, `manifest_to_safe_dict(PluginManifest)`
- Output is deterministic, bounded, safe — no raw secrets/tokens/env values echoed
- Preserved existing `load_plugins(...)` behavior and broken plugin warning

### Security fix (PM review)
- Unknown enum values (auth, permission_category, risk, data_sensitivity, event_log) are normalized to `"unknown"` in output, raw values never echoed in warnings/errors/manifest
- Warning messages use safe positional labels (e.g., `tools[0] (t): unknown risk`) without echoing raw unknown values
- Secret-like tool names are redacted to `<redacted>` in warnings and manifest output
- `_is_secret_like()` detects `sk-`, `secret`, `token`, `api_key`, `password`, `credential`, `bearer`, `auth`, `key-` patterns
- Domains/capabilities list items are filtered for secret-like values
- Removed unused `field` import

### `mini_agent/toolkits/registry_builder.py` (extended)
- Registered `inspect_plugin_manifest` tool with `ToolPermission(category="local", risk="read")`
- Handler accepts `manifest_json` string, returns safe bounded JSON metadata + validation errors

### `tests/test_plugins.py` (new, 52 tests)
- Valid manifest parsing (minimal, full, domains/capabilities, description truncation, multiple tools)
- Error cases (not dict, missing name/version, non-list tools, duplicate tool names, high-risk without/with confirmation)
- Warnings (unknown auth, permission_category, risk, data_sensitivity, event_log) — raw values not echoed
- JSON parsing (valid, malformed, non-string)
- Safe dict output (no secrets, deterministic)
- Inspection tool (valid, invalid, JSON, no raw secrets)
- Tool defaults and description truncation
- load_plugins preserved (nonexistent dir, simple plugin, broken plugin warning)
- Constants validation
- Sentinel no-leak tests (auth, permission_category, risk, data_sensitivity, event_log, domains, capabilities, tool name in warnings, combined)
- Unknown values normalized to "unknown"

## Verification

```text
python3 -m unittest tests.test_plugins tests.test_mcp_server tests.test_mini_agent
→ 225 tests OK

python3 evals/run_evals.py
→ 423 passed, 0 failed

git diff --check
→ (clean)
```

## Notes

- No commit or push performed.
- No edits to B_TASK, B_DONE, CODEX_TERMINAL_HANDOFF.md, or designs/.
- Worktree is clean — no conflicts with existing uncommitted work.
