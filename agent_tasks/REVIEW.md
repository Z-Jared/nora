# CCB Review — TASK-113: Plugin manifest schema and inspection v1

**Status: APPROVED**

## Summary

Clean implementation of manifest v1 schema parsing, validation, and safe inspection. No blocking issues.

## Key Findings

**Read-only**: `inspect_plugin_manifest` registered with `ToolPermission(category="local", risk="read")`. Handler only parses JSON input via `inspect_manifest_json()` — no plugin code execution, no external calls, no persistence.

**Security hardening** (PM fix applied):
- Unknown enum values (auth, permission_category, risk, data_sensitivity, event_log) normalized to `"unknown"` — raw values never echoed in warnings/errors/manifest output
- Secret-like tool names redacted to `<redacted>` via `_is_secret_like()` pattern matching (`sk-`, `secret`, `token`, `api_key`, `password`, `credential`, `bearer`, `auth`, `key-`)
- `domains`/`capabilities` list items filtered for secret-like values
- Warning messages use safe positional labels (e.g., `tools[0] (t): unknown risk`)

**Manifest validation**:
- Rejects: not-dict, missing name/version, non-list tools, duplicate tool names, high-risk/external-send/destructive without `requires_confirmation=True`
- Warns: unknown enum values (normalized, not rejected)
- Description truncation: manifest 500 chars, tool 300 chars

**Test coverage**: 52 tests across 10 test classes:
- Valid parsing (minimal, full, domains/capabilities, truncation, multiple tools)
- Error cases (6 tests)
- Warnings with raw value no-leak (5 tests)
- JSON parsing (valid, malformed, non-string)
- Safe dict output (deterministic, no secrets)
- Inspection tool (valid, invalid, JSON, no raw secrets)
- Tool defaults and description truncation
- `load_plugins` preserved (nonexistent dir, simple plugin, broken plugin warning)
- Constants validation (6 tests)
- Sentinel no-leak (9 tests covering all enum/list fields + combined)
- Unknown value normalization (5 tests)

## Residual Risk

None. Implementation is additive, well-tested, and security-hardened.
