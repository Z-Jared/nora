# Claude A Completion Report — TASK-062: Worker Workspace Preparation Integration

Status: ready for Codex review

## Summary

Integrated workspace lease preparation into worker claim and dispatch flows. When a worker claims or is dispatched a task, a workspace lease is automatically created. If the worker already has a lease for the same task, it is reused (returns `reused: True`). Workspace failures never block claim/dispatch.

## Changes

### `mini_agent/toolkits/registry_builder.py`

**`_prepare_worker_workspace_json` — reuse same-task lease:**
- If worker already has a lease for the *same* task_id, returns success with `reused: True` and the existing lease info (instead of error)
- If worker has a lease for a *different* task, still returns error with `existing_lease_id`

**`_try_prepare_workspace(worker_id, task_id)` — new internal helper:**
- Best-effort wrapper around `_prepare_worker_workspace_json`
- Never raises — catches all exceptions and returns error dict
- Used by claim and dispatch for non-blocking workspace preparation

**`_claim_durable_task_json` — workspace integration:**
- After successful claim, calls `_try_prepare_workspace` and includes `workspace` field in response
- Also includes workspace in `already_assigned` response path
- Workspace failure does not block claim

**`_dispatch_durable_tasks_json` — workspace integration:**
- After each assignment, calls `_try_prepare_workspace` and includes `workspace` field in each assignment entry
- Workspace failure does not block dispatch

### `evals/run_evals.py`
- Updated `eval_workspace_lease_idempotency_uniqueness` to expect `reused: True` for same-worker same-task duplicate (instead of error)
- Task-level duplicate (different worker, same task) still expects error

### `tests/test_durable_workers.py`
- Added `test_prepare_same_task_returns_reused` to `WorkspaceLeaseTests` — verifies reuse behavior
- Added `WorkspaceIntegrationTests` class with 11 tests:
  - `test_claim_auto_prepares_workspace` — claim creates workspace lease, directory exists
  - `test_dispatch_auto_prepares_workspace` — dispatch creates workspace lease, directory exists
  - `test_claim_reuses_existing_workspace` — second claim returns `reused: True` with same lease_id
  - `test_dispatch_multiple_workers_each_get_workspace` — each dispatched worker gets own lease
  - `test_claim_workspace_failure_does_not_block` — mkdir failure still allows claim
  - `test_dispatch_workspace_failure_does_not_block` — mkdir failure still allows dispatch
  - `test_claim_workspace_no_goal_leak` — workspace output has no raw goal/steps
  - `test_dispatch_workspace_no_goal_leak` — workspace output has no raw goal/steps
  - `test_claim_workspace_event_emitted` — WORKSPACE_PREPARED event recorded on claim
  - `test_dispatch_workspace_event_emitted` — WORKSPACE_PREPARED event recorded on dispatch
  - `test_dispatch_no_tasks_no_workspace` — no tasks → no workspace events

## Verification

```
$ python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 565 tests — OK

$ python3 -m unittest discover -s tests
Ran 1621 tests — OK

$ python3 evals/run_evals.py
211 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/toolkits/registry_builder.py |  30 +++++++++++++++++++++++++++---
 evals/run_evals.py                      |   8 ++++----
 tests/test_durable_workers.py           | 130 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 3 files changed
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- `claim_durable_task` and `dispatch_durable_tasks` response now include `workspace` field with lease info.
- Same-worker same-task prepare returns `reused: True` instead of error (idempotent).
- Different-worker same-task prepare still returns error (uniqueness enforced).
- Workspace failures never block claim or dispatch.
