# Claude A Completion Report

Task: TASK-048 — Durable worker auto-dispatch v1
Status: completed

## Summary

Added `dispatch_durable_tasks` registry tool that automatically assigns
pending/unassigned durable tasks to idle/online workers. Calls
`mark_stale_workers_offline()` before dispatch to ensure stale workers
(no recent heartbeat) are excluded from assignment.

## Changes

### `mini_agent/toolkits/registry_builder.py`
- Added `_dispatch_durable_tasks_json(max_assignments=10)` function:
  - Calls `durable_worker_store.mark_stale_workers_offline()` first
    to exclude stale workers (default 300s heartbeat threshold).
  - Bounds `max_assignments` to [1, 50].
  - Filters workers: `status == IDLE and not current_task_id`.
  - Filters tasks: `status == "pending" and not worker_id`.
  - Sorts tasks by `created_at` ascending, workers by `worker_id`.
  - Assigns via `durable_task_store.assign_worker()` (preserves task status).
  - Updates worker status to `ASSIGNED` with `current_task_id`.
  - Emits `TASK_STATUS_CHANGED` event per assignment (failure isolated).
  - Returns `{"dispatched": N, "assignments": [...]}` — no goal/steps leaked.
- Registered as `dispatch_durable_tasks` tool with `task` / `write` permission.

### `tests/test_durable_workers.py`
- Added `DurableWorkerDispatchTests` class with 14 tests:
  - Basic dispatch (1 worker, 1 task)
  - Multiple workers and tasks
  - `max_assignments` cap
  - No idle workers returns empty
  - No pending tasks returns empty
  - Offline workers excluded
  - Stale idle workers excluded (last_seen_at set to 2020, auto-marked offline)
  - Running workers excluded
  - Existing assigned tasks not reassigned
  - Worker/task state consistency after dispatch
  - Output bounded, no goal/steps leakage
  - Event store failure isolation
  - `max_assignments` bounded to cap
  - More tasks than workers / more workers than tasks

## Review fix

**Problem**: Dispatch only checked `status == IDLE` and `current_task_id`,
but did not exclude stale workers (no recent heartbeat, status still IDLE).

**Fix**: Added `durable_worker_store.mark_stale_workers_offline()` call at
the top of `_dispatch_durable_tasks_json()`, reusing the existing heartbeat/
offline lifecycle with the default 300s threshold. Stale workers are
transitioned to OFFLINE before the idle-worker filter runs.

## Verification run

```
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
  → 468 tests OK

python3 evals/run_evals.py
  → 182 passed, 0 failed

git diff --check
  → clean

python3 -m unittest discover -s tests
  → 1524 tests OK
```
