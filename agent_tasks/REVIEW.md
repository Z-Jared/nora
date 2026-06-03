# TASK-098 — Deterministic eval coverage for guarded scheduler retry execution v1

**Status: APPROVED**

## Review Summary

All 9 eval cases are substantive, deterministic, and cover every requirement from B_TASK.md. No runtime changes. No weak assertions, test pollution, or resource leaks.

---

## 1. Coverage of B_TASK.md Requirements

| Requirement | Eval | ✓ |
|------------|------|---|
| dry-run/no-mutation | `retry_exec_dry_run_once` | ✅ |
| non-dry-run retry | `retry_exec_non_dry_run_once` | ✅ |
| tick/loop wrapper | `retry_exec_tick_and_loop` | ✅ |
| no idle capacity | `retry_exec_no_capacity_skips` | ✅ |
| active ASSIGNED/RUNNING owner | `retry_exec_active_owner_blocks` | ✅ |
| stale execution-time guard | `retry_exec_stale_guard` | ✅ |
| closeout before retry / dispatch skipped | `retry_exec_priority_closeout_before_retry` | ✅ |
| safety no-leak | `retry_exec_safety_no_leak` | ✅ |
| compatibility | `retry_exec_compatibility` | ✅ |

All 9 requirements covered. ✅

---

## 2. `retry_exec_active_owner_blocks` — Not Vacuous

This eval proves three things for both ASSIGNED and RUNNING states:

1. **Summary reports blocked**: `summary.retry_blocked_active_worker >= 1` ✅
2. **No retry action produced**: `len(retry_results) == 0` ✅
3. **Task not mutated**: `status == "failed"`, `retry_count == 0` ✅

The eval uses `_setup_failed_task(set_worker_idle=False)` to keep the worker assigned, then calls `run_worker_lifecycle_once(dry_run=False)`. Since the planner filters out tasks with active owners, no retry action appears in results. The summary counter and task state prove the blocking is real, not vacuous.

Both ASSIGNED and RUNNING covered in the same eval (two code paths). ✅

---

## 3. `retry_exec_stale_guard` — Proves What It Claims

The eval demonstrates the planner-vs-execution gap:

1. **Planner sees retry**: Calls `plan_worker_lifecycle_actions`, asserts `retry_failed_task` action exists for the task. ✅
2. **Execution sees stale state**: Monkey-patches `ts.get_task` to return `status="completed"` for the target task. ✅
3. **Execution skips safely**: Result shows `skipped=True`, `reason="task_not_failed"`. ✅
4. **Real DB unchanged**: Reads from real DB (not mock), confirms `status=="failed"`, `retry_count==0`. ✅

The `copy.deepcopy` + `patch.object` pattern correctly isolates the mock from real DB state. The eval proves the execution-time guard catches state changes between planning and execution. ✅

---

## 4. Weak Assertions, Pollution, Flakiness, Resource Leaks

**Weak assertions**: None. All assertions check concrete values:
- `result["dry_run"] is True`
- `retry_results[0]["would_execute"] is True`
- `after_task.status == "pending"`
- `after_task.retry_count == 1`
- `retry_results[0].get("reason") == "task_not_failed"`
- `closeout_idx < retry_idx`

**Test pollution**: None. Each eval uses `tempfile.TemporaryDirectory()` with isolated DB. ✅

**Ordering flakiness**: `retry_exec_priority_closeout_before_retry` uses `enumerate` index comparison (`closeout_idx < retry_idx`), which is deterministic for the action list produced by a single run-once call. ✅

**Resource leaks**: All evals use `try/finally: db.close()` pattern. ✅

---

## 5. Runtime Changes

Confirmed: **None**. Diff only modifies `evals/run_evals.py`. B_DONE.md states "None. All evals pass against existing TASK-097 runtime." ✅

---

## Checks

- 9 evals cover all B_TASK.md requirements ✅
- `retry_exec_active_owner_blocks` not vacuous (summary + no action + no mutation) ✅
- `retry_exec_stale_guard` proves planner-sees-retry but execution-skips ✅
- No weak assertions, pollution, flakiness, or resource leaks ✅
- No runtime changes ✅
- PM verified: 358 passed, 726 tests OK, git diff --check clean ✅
