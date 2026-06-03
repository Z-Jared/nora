# TASK-097 — Guarded scheduler retry execution v1

**Status: APPROVED**

## Review Summary

The implementation correctly extends `run_worker_lifecycle_once` to execute `retry_failed_task` actions with comprehensive guards. All five guard checks are present and in correct order. Dry-run remains read-only. Output is bounded with no sensitive data leakage.

---

## 1. Retry Execution Scope

✅ `retry_failed_task` + `retry_available` only.

Lines 139-146: `reason != "retry_available"` → skip. Only `retry_available` proceeds to dry_run or execution path.

## 2. Execution-Time Guards

All five guards present in correct order:

| Guard | Skip Reason | Line |
|-------|------------|------|
| Task exists | `task_not_found` | 158-165 |
| Status still `failed` | `task_not_failed` | 166-173 |
| `retry_count < max_retries` | `retry_exhausted` | 174-181 |
| No active ASSIGNED/RUNNING worker | `retry_blocked_active_worker` | 183-200 |
| Idle capacity exists | `retry_blocked_missing_capacity` | 202-214 |
| All pass | `retry_durable_task()` | 216-225 |

Exception handling wraps `retry_durable_task()` → `retry_execution_error` on failure.

## 3. Dry-Run / Dispatch / Ordering

- **Dry-run**: Lines 147-154 return `would_execute=True`, no mutation. ✅
- **Dispatch not executed**: Only `retry_failed_task` action type is handled in this block; dispatch/closeout handled elsewhere. ✅
- **Ordering**: Planner produces closeout > retry > dispatch; `run_worker_lifecycle_once` iterates in order. `test_closeout_ahead_of_retry` verifies with `actions.index()`. ✅

## 4. Output Bounded / No Leak

Result fields are all safe: `task_id`, `retry_count`, `max_retries`, `would_execute`, `executed`, `skipped`, `reason`. No goal, steps, failure_reason, workspace path, shell/env/request/secrets.

Five dedicated leak tests:
- `test_no_goal_leak` — sentinel goal absent
- `test_no_failure_reason_leak` — "failure_reason" absent
- `test_no_steps_leak` — sentinel steps absent
- `test_no_workspace_path_leak` — "/tmp/" and "workspace_path" absent
- `test_no_shell_env_secret_leak` — sentinel absent

## 5. Test Quality

16 tests, all substantive. No vacuous passes. Key strengths:
- `test_stale_state_guard` uses mock to simulate state change between planning and execution — proves guard works
- `test_active_worker_retry_skipped` uses `subTest` for RUNNING/ASSIGNED
- `test_non_dry_run_retries_failed_task` verifies task becomes `pending` with `retry_count==1`

---

## Findings

### Minor (Non-blocking)

**`test_active_worker_retry_skipped` calls `self.setUp()` inside loop without prior `tearDown()`** (line 342): First iteration's tmpdir/db are not explicitly closed before second iteration creates new ones. `TemporaryDirectory.__del__` will clean up on GC, but explicit `self.tearDown()` before `self.setUp()` in the loop would be cleaner. Does not affect test correctness or CI stability.

---

## Checks

- `retry_failed_task` only executes when `reason == "retry_available"` ✅
- All 5 guards checked at execution time ✅
- Dry-run read-only ✅
- Dispatch not executed ✅
- closeout > retry > dispatch ordering ✅
- Output bounded, no sensitive leak ✅
- No weak/vacuous assertions ✅
- No runtime fix needed ✅
