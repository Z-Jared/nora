# Claude A Completion Report — TASK-064: Worker Workspace Sandbox Guard v1

Status: ready for Codex review

## Review Fix

**Must Fix #1 — sandbox guard must reject offline/idle workers**

Added `WorkerStatus.OFFLINE` and `WorkerStatus.IDLE` checks to `_resolve_and_validate_lease()` before the `current_task_id` check. A worker that has gone offline or returned to idle cannot use sandbox tools even if they still have a stale lease and `current_task_id`.

Regression tests added:
- `test_get_workspace_offline_worker_returns_error`
- `test_validate_path_offline_worker_returns_error`
- `test_get_workspace_idle_worker_with_task_id_returns_error`
- `test_validate_path_idle_worker_with_task_id_returns_error`

## Summary

Added two read-only sandbox guard tools and a shared validation helper that ensure worker file/command operations can only target paths within their active workspace lease directory.

## Changes

### `mini_agent/toolkits/registry_builder.py`

**`_resolve_and_validate_lease(worker_id, task_id)` — shared helper:**
- Validates worker exists
- Validates `worker.status` is not OFFLINE or IDLE
- Validates `worker.current_task_id == task_id`, task exists, `task.worker_id == worker_id`
- Validates lease exists for the worker and `lease.task_id == task_id`
- Returns `(lease, None)` on success or `(None, error_dict)` on failure
- Used by both new tools to avoid duplication

**`get_worker_workspace(worker_id, task_id)` — read-only tool:**
- Returns `DurableWorkspaceLease.to_dict()` if validation passes
- Returns bounded JSON error otherwise
- Registered with `risk="read"` permission

**`validate_worker_workspace_path(worker_id, task_id, path)` — read-only tool:**
- Resolves the target path via `Path.resolve()` (normalizes `..`, symlinks)
- Checks `resolved.relative_to(ws_root.resolve())` to ensure path is within workspace
- Path traversal (`../../etc/passwd`), absolute path escape (`/etc/passwd`), and any path outside workspace return `{"error": "path 不在 workspace 内", ...}`
- Empty path returns error
- On success returns `{"valid": True, "path": ..., "workspace_path": ..., "lease_id": ...}`
- Registered with `risk="read"` permission

### `tests/test_durable_workers.py`
- Added `WorkspaceSandboxGuardTests` class with 20 tests:
  - **get_worker_workspace** (7 tests): returns lease, no lease error, unknown worker error, task mismatch error, worker not executing task error, offline worker error, idle worker error
  - **validate_worker_workspace_path** (13 tests): path inside workspace, workspace root itself, `..` traversal escape, absolute path escape, no lease error, unknown worker error, empty path error, worker-task mismatch error, lease for different task error, no goal leak, `..` that stays within workspace (normalized), offline worker error, idle worker error

## Verification

```
$ python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 585 tests — OK

$ python3 -m unittest discover -s tests
Ran 1641 tests — OK

$ python3 evals/run_evals.py
228 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/toolkits/registry_builder.py | 106 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---------
 tests/test_durable_workers.py           | 172 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 2 files changed
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- Both tools are read-only (`risk="read"`) — they validate paths but do not create files.
- The `_resolve_and_validate_lease` helper is reusable for future sandbox enforcement in file edit, shell command, and other tools.
- `Path.resolve()` handles symlink normalization and `..` traversal safely.
