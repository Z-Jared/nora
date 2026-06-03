# Claude B Done

Owner: Claude B
Status: completed

## Task

TASK-098: Deterministic eval coverage for guarded scheduler retry execution v1

## Summary

Added 9 eval cases in `evals/run_evals.py` covering guarded scheduler retry execution:

1. **retry_exec_dry_run_once** — `run_worker_lifecycle_once(dry_run=True)` returns retry would-execute metadata and does not mutate failed task state (retry_count, status).

2. **retry_exec_non_dry_run_once** — `run_worker_lifecycle_once(dry_run=False)` retries a safe retryable failed task, moving it to `pending` and incrementing `retry_count` from 0 to 1.

3. **retry_exec_tick_and_loop** — Scheduler tick and scheduler loop wrappers execute the retry path when `dry_run=False`, verifying task state mutation through both wrappers.

4. **retry_exec_active_owner_blocks** — Active owner worker (both ASSIGNED and RUNNING states) blocks retry execution. Planner does not produce retry action; summary reports `retry_blocked_active_worker >= 1`; task status and retry_count unchanged.

5. **retry_exec_stale_guard** — Stale execution-time guard: planner sees retry action (task is failed), but `get_task` returns changed state (completed) at execution time. Execution skips with `task_not_failed` reason; task NOT retried.

6. **retry_exec_no_capacity_skips** — No idle capacity (worker set offline) causes retry to skip with `retry_blocked_missing_capacity` reason; task status and retry_count remain unchanged.

7. **retry_exec_priority_closeout_before_retry** — Ready closeout (`finalize_ready_workspace_merge`) appears before retry (`retry_failed_task`) in execution results; dispatch actions remain skipped.

8. **retry_exec_safety_no_leak** — Both dry-run and non-dry-run outputs do not leak goal, secret, step, failure reason, env, request, or workspace path sentinels.

9. **retry_exec_compatibility** — After retry execution, planner, explain, scheduler tick, scheduler loop, run-once, worker/task registry, claim, and dispatch all still work.

## Runtime Changes

None. All evals pass against existing TASK-097 runtime.

## Evidence

```
python3 evals/run_evals.py — 358 passed, 0 failed
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent — 726 tests, OK
git diff --check — clean
```

## Diff

Only `evals/run_evals.py` modified (no runtime changes).
