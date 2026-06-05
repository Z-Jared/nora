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

---

# TASK-129 Review: CLI wake/setup/status UX v1

**Status: APPROVED**

## Summary

Claude A implemented the first CLI workbench UX pass: `/wake`, `/model`, `/workers`, a richer startup banner, and common error recovery hints. PM initial review found one blocking startup worker-summary bug; Claude A fixed it and added a focused regression test.

## PM Fix Verified

- `_worker_state_summary()` now resolves worker DONE files with `agent.split("-")[-1].upper()`, so `claude-a` maps to `A_DONE.md` and `claude-b` maps to `B_DONE.md`.
- `tests.test_cli.CLIWorkersCommandTests.test_banner_detects_done_file` covers startup/banner detection of `.ccb/workspaces/claude-a/agent_tasks/A_DONE.md`.
- PM manual probe returned `Workers: claude-a: done, claude-b: no done file`.

## Coverage

- `/wake`: project wake panel, knowledge-file presence, missing-file recovery, non-git recovery.
- `/model`: provider/model/base URL/key presence diagnostics without key leakage.
- `/workers`: missing `.ccb`, task display, DONE-ready status, startup worker summary.
- Error recovery: 401, timeout, model not found, rate limit, missing key, port in use, normal response no hint, agent response hint append.
- Help text includes the new CLI workbench commands.

## Evidence

- `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` → 207 tests OK
- `python3 evals/run_evals.py` → 497 passed, 0 failed
- `git diff --check` → clean
- PM targeted check: `python3 -m unittest tests.test_cli.CLIWorkersCommandTests.test_banner_detects_done_file` → OK

## Verdict

Approved for integration. TASK-130 remains open because the current B eval patch was authored before TASK-129 was integrated and does not yet cover `/wake`, `/model`, or `/workers`.

---

# TASK-130 Review: CLI UX smoke/eval coverage

**Status: APPROVED**

## Summary

Claude B revised TASK-130 after TASK-129 was integrated at `aa3c084`. The final eval patch covers the real CLI workbench surface rather than the older `/doctor`-only surface.

## Coverage

- Startup banner: no-model/key-missing diagnostics, common command hints, configured provider/model, no key leakage.
- Worker summary: startup banner detects `.ccb/workspaces/claude-a/agent_tasks/A_DONE.md` and `B_DONE.md` as done.
- `/wake`: project panel with workspace, branch, knowledge file status and active task summary; non-project recovery guidance.
- `/model`: provider/model/base URL/key-safe diagnostics and no-settings setup hint.
- `/workers`: CCB A/B task and DONE status, ready-for-PM-review detection, missing `.ccb` recovery.
- Error recovery: 401/unauthorized model failure appends API-key recovery hint to normal agent responses.
- Output structure: `/wake`, `/model`, `/workers`, `/help`, `/doctor` stay plain text/Markdown and do not emit raw JSON.

## PM Review Notes

- B worktree was based on `aa3c084 Add CLI wake and worker status UX`.
- No runtime implementation files were modified.
- Grep found no new `or True` / tautological TASK-130 assertions.

## Evidence

- `python3 evals/run_evals.py` → 508 passed, 0 failed
- `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` → 207 tests OK
- `git diff --check` → clean

## Verdict

Approved for integration. This closes the CLI UX implementation + deterministic eval coverage pair for TASK-129/TASK-130.
