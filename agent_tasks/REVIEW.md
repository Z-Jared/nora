# CCB Code Review Report

Reviewed: TASK-092 Deterministic eval coverage for scheduler loop v1
Worker: Claude B
Status: **APPROVED**

---

## Review Scope

### 1. Deterministic and Offline

**Verdict: ✅ DETERMINISTIC**

All 11 eval cases are deterministic and offline:

- ✅ Uses `tempfile.TemporaryDirectory()` for isolation
- ✅ Uses `build_default_registry` with `confirm_action=lambda _: True`
- ✅ No live LLM calls
- ✅ No interactive terminal prompts
- ✅ No external state dependencies
- ✅ No network calls
- ✅ No timing dependencies
- ✅ Reproducible — same results every run

### 2. Eval Coverage Completeness

**Verdict: ✅ COMPREHENSIVE**

11 eval cases covering all key scheduler loop scenarios:

1. **`eval_loop_dry_run_no_mutation`** — Default dry-run loop does not mutate task/worker/lease/project root/workspace
2. **`eval_loop_max_ticks_and_limit`** — Bounded `max_ticks` (0→1, 999→10) and `limit` (0→1, 999→100) clamping
3. **`eval_loop_stop_when_idle_true`** — `stop_when_idle=True` stops early on empty state
4. **`eval_loop_stop_when_idle_false`** — `stop_when_idle=False` runs the requested bounded tick count
5. **`eval_loop_non_dry_run_closeout`** — Non-dry-run finalizes ready closeouts, does not dispatch pending tasks
6. **`eval_loop_dispatch_wait_blocked`** — Dispatch blocked with `reason=dispatch_blocked_in_tick`, wait skipped with `reason=wait_action`
7. **`eval_loop_record_event_true`** — Loop scheduler event is recorded with safe bounded metadata
8. **`eval_loop_record_event_false`** — `record_event=False` avoids loop event recording
9. **`eval_loop_bad_params`** — Bad `max_ticks`, `limit`, `dry_run`, `release_workspace`, `stop_when_idle`, `record_event` return bounded errors; valid clamps verified
10. **`eval_loop_safety_no_leak`** — Output does not leak goal, steps, file content, reviewer summary, shell/env/request sentinels, workspace paths, or secrets
11. **`eval_loop_compatibility`** — Existing tools (scheduler tick, run-once, planner, batch finalize, single-task finalize, closeout candidate query, worker/task registry, claim, dispatch) still work after loop call

### 3. PM-Identified Weak Assertion Fixes

**Verdict: ✅ FIXED**

**`eval_loop_non_dry_run_closeout` (lines from diff):**
- ✅ Rewrote to verify that when ready closeout + idle worker + pending task coexist:
  - `dry_run=False` finalizes closeout
  - Pending task remains `pending`/unassigned
  - Idle worker stays untasked
  - Dispatch action has `skipped=True, reason=dispatch_blocked_in_tick` in tick event payload

**`eval_loop_dispatch_wait_blocked` (lines from diff):**
- ✅ Rewrote to assert concrete reason labels from tick event payload `actions` array:
  - Dispatch action has `reason=dispatch_blocked_in_tick`, `skipped=True`
  - Wait action has `reason=wait_action`, `skipped=True`

### 4. Safety and No-Leak

**Verdict: ✅ SAFE**

**Sentinel values used:**
- `_LIFECYCLE_SENTINEL_GOAL`
- `_LIFECYCLE_SENTINEL_SECRET`
- `_LIFECYCLE_SENTINEL_STEP`
- `_LIFECYCLE_SENTINEL_FILE`
- `_LIFECYCLE_SENTINEL_REVIEWER`
- `_LIFECYCLE_SENTINEL_SHELL`
- `_LIFECYCLE_SENTINEL_REQUEST`
- `_LIFECYCLE_SENTINEL_ENV`

**Safety assertions in `eval_loop_safety_no_leak`:**
- ✅ Goal text absent from output (sentinel)
- ✅ Secret text absent from output (sentinel)
- ✅ Step text absent from output (sentinel)
- ✅ File content absent from output (sentinel)
- ✅ Reviewer summary absent from output (sentinel)
- ✅ Shell output absent from output (sentinel)
- ✅ Request string absent from output (sentinel)
- ✅ Env sentinel absent from output (sentinel)
- ✅ Workspace path fragment (`.workspaces`) absent from output
- ✅ Verified for both dry-run and non-dry-run

### 5. Regression Prevention Quality

**Verdict: ✅ STRONG**

Evals prevent key TASK-091 regressions:

**Loop behavior:**
- ✅ Dry-run does not mutate state
- ✅ Non-dry-run finalizes closeouts but does not dispatch pending tasks
- ✅ `stop_when_idle=True` stops early on empty state
- ✅ `stop_when_idle=False` runs all requested ticks
- ✅ `max_ticks` and `limit` clamped correctly

**Event recording:**
- ✅ `record_event=True` records SCHEDULER_DECISION event with safe metadata
- ✅ `record_event=False` avoids event recording
- ✅ Event payload contains scheduler, loop_id, dry_run, max_ticks, ticks_run, stopped_reason

**Dispatch/wait blocking:**
- ✅ Dispatch actions blocked with `reason=dispatch_blocked_in_tick`
- ✅ Wait actions skipped with `reason=wait_action`
- ✅ Verified via tick event payload `actions` array

**Parameter validation:**
- ✅ Bad max_ticks (string, bool) returns error
- ✅ Bad limit (string, bool) returns error
- ✅ Bad dry_run, release_workspace, stop_when_idle, record_event returns error
- ✅ Valid clamps (0→1, 999→10) work correctly

**Compatibility:**
- ✅ Scheduler tick still works after loop
- ✅ Run-once still works after loop
- ✅ Planner still works after loop
- ✅ Batch finalize still works after loop
- ✅ Single-task finalize still works after loop
- ✅ Closeout candidate query still works after loop
- ✅ Worker/task registry still works after loop
- ✅ Claim and dispatch still work after loop

### 6. Assertion Quality

**Verdict: ✅ SUBSTANTIVE**

**Positive assertions verify specific values:**
- ✅ `dry_run=False`, `executed_count >= 1`, `failed_count == 0`
- ✅ Pending task status `pending`, worker_id `None` or empty
- ✅ Idle worker current_task_id `None` or empty
- ✅ Dispatch action `skipped=True`, `reason=dispatch_blocked_in_tick`
- ✅ Wait action `skipped=True`, `reason=wait_action`
- ✅ `max_ticks >= 1`, `max_ticks <= 10`
- ✅ Event payload fields: scheduler, loop_id, dry_run, max_ticks, ticks_run, stopped_reason

**Negative assertions verify safety:**
- ✅ 8 sentinels absent from output
- ✅ Workspace path fragment absent from output
- ✅ No goal, steps, file content, secrets leaked

**No empty or misleading assertions:**
- ✅ All assertions check specific conditions
- ✅ No assertions that always pass
- ✅ No misleading comments

### 7. No Runtime Changes by Claude B

**Verdict: ✅ CLEAN**

From `B_DONE.md`:
- ✅ "No runtime implementation changes required"
- ✅ "No push was performed by Claude B"

**Diff verification:**
- ✅ Only `evals/run_evals.py` modified (410 lines added)
- ✅ `agent_tasks/B_DONE.md` and `agent_tasks/PM_INBOX.md` are task status files, not runtime code
- ✅ No changes to runtime code (registry_builder.py, durable_workers.py)
- ✅ No eval depends on incorrect TASK-091 behavior

---

## Test Gaps / Residual Risks

**None identified.**

All critical scheduler loop behaviors are covered:
- ✅ Dry-run and non-dry-run modes
- ✅ max_ticks and limit bounds
- ✅ stop_when_idle early stop
- ✅ Event recording (on/off)
- ✅ Parameter validation (bad types, clamping)
- ✅ Safety (no leakage of goals, steps, file content, secrets)
- ✅ Compatibility (9 existing tools verified)
- ✅ Dispatch/wait blocking with reason labels (PM fix applied)

---

## Checks Run

```text
python3 evals/run_evals.py
323 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 651 tests — OK

python3 -m unittest discover -s tests
Ran 2010 tests — OK (only existing warning: failed to load plugin broken.py: bad)

git diff --check
OK
```

---

## Findings

### Must Fix

**None** — implementation is production-ready.

### Suggestions

**None** — eval coverage is comprehensive and well-structured.

---

## Recommendation

**APPROVE and merge.**

TASK-092 provides strong deterministic eval coverage for TASK-091 scheduler loop. All critical regression scenarios are covered: dry-run/non-dry-run modes, max_ticks/limit bounds, stop_when_idle, event recording, parameter validation, safety (no leakage), and compatibility (9 existing tools). PM-identified weak assertions have been properly fixed with concrete reason label verification from tick event payload. No runtime changes by Claude B.

**Next Action**: PM can proceed with git commit and push.
