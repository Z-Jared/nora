# TASK-127 Review: Context compiler local skill catalog bridge v1

**Status: APPROVED**

## Summary

Clean integration of TASK-125 local skill manifest discovery into ContextCompiler. PM review fixes properly sanitize diagnostic messages and handle malformed `skill_manifest_paths` input. 15 tests cover all key scenarios.

## Review Criteria Assessment

### 1. Read-Only Behavior ✅
- `discover_local_skill_manifests_json()` is read-only (no loading/installation/execution)
- No state mutation in `_combine_skill_manifests()` or `_skill_context_section()`
- Discovery bound to `self.root` via `project_root=str(self.root)`

### 2. Path Safety ✅
- `_sanitize_discovery_message()` (lines 19-59) strips raw paths from all discovery diagnostics
- Pattern: `"path not found: <path>"` → `"path not found"` (8 message types handled)
- Manifest parse errors: `"[<path>] <error>"` → `"<error>"` (prefix stripped)
- Underlying discovery handles traversal, absolute paths, hidden/denied dirs

### 3. Malformed Input ✅
- Non-string `skill_manifest_paths`: bounded error section (line 176-178)
- Non-list JSON string: bounded error section (line 170-172)
- Invalid JSON: bounded error section (line 173-175)
- Error message: `"skill_manifest_paths must be a JSON list or array of strings"` — no raw input echoed

### 4. Secret-Like Values ✅
- `manifest_to_safe_dict()` uses `_safe_str` throughout
- Test: `test_secret_like_manifest_values_do_not_leak` verifies `sk-TOKEN-secret-skill` absent

### 5. Budget Enforcement ✅
- `_append_if_fits()` enforces `max_chars` budget
- Test: `test_context_budget_applies_to_discovered_skill_context` verifies bounded output

### 6. Compatibility ✅
- Existing git status, file outlines, knowledge excerpts, RAG, memory records preserved
- Tests verify coexistence with existing features

## PM Review Fixes Verified

**Fix 1: `_sanitize_discovery_message()`** — Maps 8 known discovery message patterns to coarse labels without raw paths. Applied to all discovery errors/warnings before including in Skill Context Preview.

**Fix 2: Malformed JSON string `skill_manifest_paths`** — Non-empty string that fails JSON parsing or parses to non-list returns bounded diagnostic section. Raw input string not echoed.

## Test Coverage (15 tests)

| Category | Tests |
|----------|-------|
| Basic behavior | No paths keeps existing behavior |
| Valid discovery | Single file, directory with multiple, registry integration |
| Combination | Manual + local manifests combine |
| Path safety | Traversal, hidden/denied, missing paths — all sanitized |
| Malformed input | JSON string paths, non-array, non-list |
| Safety | Secret-like values don't leak |
| Budget | Context budget applies |
| Compatibility | Git status, file outlines |

## Evidence

- `python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent` → 333 tests OK
- `python3 evals/run_evals.py` → 487 passed, 0 failed
- `git diff --check` → clean

## Verdict

Implementation is clean, well-tested, and properly sanitized. All PM review fixes verified. APPROVED.

---

# TASK-128 Review: Deterministic eval coverage for context compiler local skill catalog bridge v1

**Status: APPROVED**

## Summary

10 deterministic offline evals for TASK-127 context compiler local skill catalog bridge. All PM review fixes verified. No runtime changes.

## Coverage

| # | Eval | Key assertions |
|---|------|----------------|
| 1 | `valid_file` | Section present, skill name present, UNTRUSTED framing |
| 2 | `directory_discovery` | 3 skills found, deterministic (run-twice comparison) |
| 3 | `registry` | JSON string paths accepted, permission = workspace/read |
| 4 | `combined` | Manual + local manifests both appear |
| 5 | `path_safety` | Traversal, absolute, hidden, denied all rejected |
| 6 | `malformed_input` | Specific diagnostic message asserted; raw input NOT echoed |
| 7 | `secret_no_leak` | Secret manifest fields, raw path sentinels, raw file content all absent |
| 8 | `read_only` | Task, worker, AND event counts unchanged (PM fix) |
| 9 | `registry_root_binding` | Workspace manifest found; external manifest NOT found (PM fix) |
| 10 | `compatibility` | Manual manifests, git status, knowledge excerpts, discover/preview/permissions all work |

## PM Fixes Verified

1. **No `or True` tautologies** — grep confirms zero occurrences in TASK-128 code
2. **Read-only includes worker count** — `list_workers` before/after checked alongside tasks/events
3. **Registry root binding** — dedicated eval verifies workspace-bound manifest discovered, external manifest rejected
4. **Malformed input diagnostic** — asserts exact string `"skill_manifest_paths must be a JSON list or array of strings"`

## Findings

No blocking issues. Evals are deterministic, substantively assertive, and cover all TASK-128 requirements.
