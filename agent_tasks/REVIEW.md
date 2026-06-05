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

---

# TASK-131 Review: CLI setup/config and response-status UX v1

**Status: APPROVED**

## Summary

Claude A implemented the requested CLI setup/config guidance and deterministic response-status output. Codex PM did not apply A's raw worktree diff because the CCB worktree was stale at `67a1145` and included already-integrated TASK-129 changes; only the TASK-131 increment was manually ported onto current main.

## Coverage

- `/setup` and `/config` alias show provider/model/base URL/API-key presence without leaking key values.
- Setup guidance lists safe placeholder env keys for openai-compatible, anthropic, and gemini.
- Diagnostics cover missing keys, 401/403, timeout, port conflicts, rate limits, and provider/model mismatch.
- Normal prompt and multiline input emit deterministic model-call started/completed status lines around `agent.run(...)`.
- Slash commands, blank input, and exit do not emit model-call status noise.
- Help text and startup common commands include `/setup`.

## Review Notes

- The status output is intentionally phase-level only and does not expose hidden reasoning or chain-of-thought.
- The implementation stays inside CLI/test scope and does not change model provider semantics, runtime scheduling, or eval harness behavior.
- Existing TASK-129 `/wake`, `/model`, `/workers`, and recovery-hint behavior remains compatible.

## Evidence

- `python3 -m unittest tests.test_cli` → 74 tests OK
- `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` → 220 tests OK
- `python3 evals/run_evals.py` → 508 passed, 0 failed
- `git diff --check` → clean

## Verdict

Approved for integration. TASK-132 remains open and should now be rerun by Codex B against the integrated TASK-131 surface.

---

# TASK-132 Review: CLI setup/status UX deterministic eval coverage

**Status: APPROVED**

## Summary

Claude B added deterministic offline eval coverage for the integrated TASK-131 CLI setup/config and response-status surface. Codex PM manually integrated the eval patch, strengthened the missing-key assertion, and corrected the completion report count from 11 to 10 eval cases.

## Coverage

- `/setup` shows provider/model/base URL/API-key presence.
- `/setup` lists openai-compatible, anthropic, and gemini env keys.
- Placeholder setup guidance uses safe placeholder text and does not leak configured fake secrets.
- Error guidance covers `401 Unauthorized`, exact `API key 缺失`, required `LLM_API_KEY`, and provider/model mismatch.
- `/config` returns the same output as `/setup`.
- Normal prompt emits deterministic model-call status lines.
- Slash commands, blank input, and exit do not emit model-call status noise.
- Status/setup/config output avoids chain-of-thought markers, hidden-reasoning markers, raw JSON, and API key leakage.

## PM Review Notes

- No runtime files were modified.
- Grep found no new `or True` or tautological TASK-132 assertions.
- PM strengthened `eval_cli_setup_guidance_for_errors()` to require exact missing-key text instead of a broad `or` condition.

## Evidence

- `python3 evals/run_evals.py` → 518 passed, 0 failed
- `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` → 220 tests OK
- `git diff --check` → clean

## Verdict

Approved for integration. This closes the CLI setup/status UX implementation + deterministic eval coverage pair for TASK-131/TASK-132.

---

# TASK-133 Review: CLI slash launcher and welcome polish v2

**Status: APPROVED**

## Summary

Claude A implemented the requested slash launcher and welcome polish direction, but its CCB worktree was stale at `edca78e` and did not include the integrated TASK-131/TASK-132 CLI surface. Codex PM manually ported the TASK-133 increment onto current main, preserved `/setup` and response-status behavior, and avoided unrelated stale diff.

## Findings

- PM integration fix: A's original launcher omitted `/setup`, despite TASK-133 requiring `/`, `/wake`, and `/setup` as startup next actions. The integrated version includes `/setup` in both the launcher and banner next-action hint.
- PM scope fix: A's original patch added prefix dispatch/suggestion behavior (`/stat` → `/status`) that was not required for TASK-133. The integrated version keeps the scope to exact `/` launcher behavior.

## Coverage

- Exact `/` returns a grouped command launcher/menu.
- Launcher includes Start, Project, Workers, Memory / Tasks / Context, Diagnostics, and Help groups.
- Launcher includes `/wake`, `/setup`, `/model`, `/workers`, `/status`, `/test`, and `/help`.
- `/` does not call `agent.run(...)` and does not emit model-call status lines.
- Banner adds a next-action hint for `/`, `/wake`, and `/setup` while preserving workspace, LLM, tools, active task, and worker summary behavior.
- Unknown slash commands now point users to `/` and `/help`.

## Evidence

- `python3 -m unittest tests.test_cli` → 79 tests OK
- `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` → 225 tests OK
- `python3 evals/run_evals.py` → 518 passed, 0 failed
- `git diff --check -- mini_agent/cli.py tests/test_cli.py` → clean

## Verdict

Approved for integration. TASK-134 remains open for deterministic eval coverage against the integrated TASK-133 surface.
