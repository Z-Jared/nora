# Claude A Completion Report — TASK-060: Worker Workspace Lease / Isolation v1

Status: ready for Codex review

## Review Fix

Two blockers fixed:

**Blocker 1 — mkdir failure must not create lease**
- Changed: `prepare_worker_workspace` now returns bounded JSON error when `Path.mkdir()` raises `OSError`, and does NOT create a lease or emit `WORKSPACE_PREPARED` event.
- Regression test: `test_mkdir_failure_returns_error_no_lease` — creates a file at `.workspaces` path, verifies error returned and no lease in store.

**Blocker 2 — Worker must be actively assigned to the task**
- Changed: Added two new checks:
  - `worker.status == IDLE` → returns error (must be assigned/running/paused)
  - `worker.current_task_id != task_id` → returns error
  - `task.worker_id == worker_id` check still retained
- Regression tests:
  - `test_prepare_idle_worker_returns_error` — idle worker with matching task.worker_id but current_task_id=None → error
  - `test_prepare_worker_current_task_mismatch_returns_error` — worker assigned to t1, tries to prepare for t2 → error

## Summary

Added minimal workspace lease system for durable workers: when a worker is assigned a task, `prepare_worker_workspace` provisions a safe isolated directory and records the lease. `release_worker_workspace` cleans up the lease (without deleting the filesystem directory).

## Changes

### `mini_agent/durable_workers.py`
- Added `_next_lease_id()` helper: auto-generates `wlease_N` IDs
- Added `DurableWorkspaceLease` dataclass: `lease_id`, `worker_id`, `task_id`, `workspace_path`, `created_at`
- Added `WorkspaceLeaseStore` class with dual SQLite/JSONL backend:
  - `create_lease(worker_id, task_id, workspace_path) -> DurableWorkspaceLease`
  - `get_lease_by_worker(worker_id) -> Optional[DurableWorkspaceLease]`
  - `get_lease_by_task(task_id) -> Optional[DurableWorkspaceLease]`
  - `release_lease(lease_id) -> bool`
  - SQLite table `workspace_leases` with indexes on `worker_id` and `task_id`

### `mini_agent/durable_events.py`
- Added `WORKSPACE_PREPARED = "workspace_prepared"` and `WORKSPACE_RELEASED = "workspace_released"` constants
- Registered both in `VALID_EVENT_TYPES`

### `mini_agent/toolkits/registry_builder.py`
- Wired `WorkspaceLeaseStore(db=db)` into registry as `workspace_lease_store`
- Added `_prepare_worker_workspace_json(worker_id, task_id)`:
  - Validates worker exists, not offline, not idle
  - Validates `worker.current_task_id == task_id`
  - Validates task exists and `task.worker_id == worker_id`
  - Checks no existing lease for worker or task
  - Creates directory; **mkdir failure returns error, no lease created**
  - Records lease, emits `WORKSPACE_PREPARED` event
  - Event store failure does not block lease creation
- Added `_release_worker_workspace_json(worker_id)`:
  - Validates worker exists, finds active lease
  - Deletes lease, emits `WORKSPACE_RELEASED` event
  - Returns `{"released": true/false, ...}`
  - Does NOT delete filesystem directory
- Registered both as `prepare_worker_workspace` and `release_worker_workspace` tools

### `tests/test_durable_workers.py`
- Added `WorkspaceLeaseTests` class with 16 tests:
  - `test_prepare_basic` — happy path: lease created, directory exists
  - `test_prepare_unknown_worker_returns_error`
  - `test_prepare_offline_worker_returns_error`
  - `test_prepare_idle_worker_returns_error` — **new** idle + task.worker_id matching
  - `test_prepare_unknown_task_returns_error`
  - `test_prepare_task_not_assigned_to_worker_returns_error`
  - `test_prepare_worker_current_task_mismatch_returns_error` — **new** current_task_id mismatch
  - `test_prepare_worker_already_has_lease_returns_error`
  - `test_prepare_task_already_leased_returns_error`
  - `test_release_basic` — release existing lease
  - `test_release_no_lease_returns_released_false`
  - `test_release_unknown_worker_returns_error`
  - `test_output_bounded_no_goal_leak` — no raw goal/steps in output
  - `test_event_failure_does_not_block_prepare`
  - `test_event_failure_does_not_block_release`
  - `test_prepare_emits_safe_event` — event payload has no raw goal/steps
  - `test_mkdir_failure_returns_error_no_lease` — **new** mkdir fails → error, no lease

## Verification

```
$ python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 553 tests — OK

$ python3 evals/run_evals.py
206 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/durable_events.py              |   4 ++++
 mini_agent/durable_workers.py             | 153 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 mini_agent/toolkits/registry_builder.py   | 142 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 tests/test_durable_workers.py             | 170 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 4 files changed
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- `release_worker_workspace` does NOT delete the filesystem directory (data safety).
- Event store failures never block lease operations.
- Worker must be actively assigned (current_task_id match) before workspace can be prepared.
