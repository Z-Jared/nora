# Claude A — Completion Report

Owner: Claude A
Task: TASK-097 — Guarded scheduler retry execution v1
Status: **DONE** (PM fixes applied)

## Summary

Extended guarded worker lifecycle execution so scheduler run-once/tick/loop can execute safe retry actions for failed durable tasks when `dry_run=False`.

## Changes

### `mini_agent/toolkits/registry_builder.py` (+~90 lines)

**`run_worker_lifecycle_once` — `retry_failed_task` execution:**
- `dry_run=True`: reports `would_execute=True`, no mutation.
- `dry_run=False`: re-checks guards at execution time:
  1. Task exists and status is still `failed`.
  2. `retry_count < max_retries`.
  3. No active ASSIGNED/RUNNING worker attached.
  4. **PM fix:** Idle capacity exists (`status==IDLE` and `current_task_id` empty). If no idle capacity → `retry_blocked_missing_capacity`.
  5. All guards pass → calls `durable_task_store.retry_durable_task()`.
  6. Any failure → safe `retry_execution_error` outcome.

**Tick/Loop wrappers:** No changes needed — retry flows through `_run_worker_lifecycle_once_json` → tick → loop automatically.

### `tests/test_durable_workers.py` (+~200 lines)

**`RetryExecutionTests`** (16 tests):
- `test_dry_run_does_not_mutate_failed_task` — dry_run sees retryable, no mutation.
- `test_non_dry_run_retries_failed_task` — executes retry, task becomes pending.
- `test_tick_can_execute_retry` — tick wrapper executes retry.
- `test_loop_can_execute_retry` — loop wrapper executes retry.
- `test_exhausted_retry_skipped` — exhausted retries not mutated.
- `test_active_worker_retry_skipped` — **PM fix:** covers both ASSIGNED and RUNNING via subTest.
- `test_no_idle_capacity_skips_retry` — **PM fix:** no idle workers → `retry_blocked_missing_capacity`, no mutation.
- `test_stale_state_guard` — **PM fix:** mock intercepts execution-time `get_task` to return cancelled; proves guard catches stale state.
- `test_closeout_ahead_of_retry` — ordering preserved.
- `test_no_goal_leak` — goal not in output.
- `test_no_failure_reason_leak` — failure_reason not in output.
- `test_no_steps_leak` — **PM fix:** steps not in output.
- `test_no_workspace_path_leak` — **PM fix:** workspace path not in output.
- `test_no_shell_env_secret_leak` — **PM fix:** shell/env secret not in output.
- `test_compatibility_with_planner` — planner still sees retryable tasks.
- `test_compatibility_with_explain` — explain still sees retry_available.

## PM Fixes

1. **Idle capacity guard:** Added `retry_blocked_missing_capacity` check before calling `retry_durable_task`. Consistent with explain semantics.
2. **ASSIGNED+RUNNING coverage:** `test_active_worker_retry_skipped` now uses `subTest` for both statuses.
3. **Stale state guard:** Uses mock to return cancelled at execution-time `get_task` check, proving the guard works.
4. **Safety no-leak:** Added steps, workspace path, shell/env/secret sentinel tests.

## Verification

```text
WorkerLifecycleRunOnceTests + SchedulerTickTests + SchedulerLoopTests → 71 OK
RetryExecutionTests → 16 OK
test_durable_workers (559) → OK
broader suite (726) → OK
evals → 349 passed, 0 failed
git diff --check → clean
```

## Boundaries

- ✅ Only edited registry_builder.py and test_durable_workers.py
- ✅ No B_TASK/B_DONE, CODEX_TERMINAL_HANDOFF.md, designs/
- ✅ No commit/push
- ✅ Dry-run remains read-only, no mutation
- ✅ Retry execution uses existing `retry_durable_task` primitive
- ✅ Bounded safe metadata only, no goal/steps/failure_reason/workspace path leak
