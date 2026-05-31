# Claude A Completion Report — TASK-034: Durable Worker Task Claim v1

Status: ready for Codex review

## Summary

Added `claim_durable_task(worker_id)` registry tool that lets a registered online worker claim the oldest pending, unassigned durable task. On claim, the task's `worker_id` is updated and the worker transitions to `assigned` status with `current_task_id` set. A safe durable event is recorded on success.

## Changes

### `mini_agent/toolkits/registry_builder.py`
- Added `_claim_durable_task_json(worker_id)` handler (lines 718–772):
  - Strips and validates `worker_id`, returns JSON error if empty
  - Looks up worker; returns JSON error if unknown or offline
  - If worker already has `current_task_id`, returns existing assignment (`already_assigned: true`)
  - Finds oldest pending task with empty `worker_id` from `list_tasks(limit=500)`
  - Returns `{claimed: false}` if no task available (no mutation)
  - Calls `durable_task_store.assign_worker()` to set task `worker_id` without changing status
  - Updates worker to `status=assigned` and `current_task_id`
  - Records `TASK_STATUS_CHANGED` event with safe metadata only
  - Event write failure is caught and does not prevent the claim
- Registered `claim_durable_task` tool with `ToolPermission(category="task", risk="write")`

### `tests/test_durable_workers.py`
- Added `DurableWorkerClaimTests` class with 12 tests:
  - `test_idle_worker_claims_oldest_pending_task`
  - `test_claim_updates_task_worker_id_and_worker_state`
  - `test_claim_does_not_change_task_status`
  - `test_unknown_worker_returns_error`
  - `test_offline_worker_returns_error`
  - `test_worker_with_current_task_returns_existing`
  - `test_no_available_task_returns_claimed_false`
  - `test_no_available_task_does_not_mutate_worker`
  - `test_claim_emits_safe_event`
  - `test_broken_event_store_does_not_prevent_claim`
  - `test_claim_empty_worker_id_returns_error`
  - `test_claim_whitespace_worker_id_returns_error`

## Verification

```
$ python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 453 tests — OK

$ python3 evals/run_evals.py
152 passed, 0 failed

$ python3 -m unittest discover -s tests
Ran 1321 tests — OK

$ git diff --check -- mini_agent/toolkits/registry_builder.py tests/test_durable_workers.py
OK
```

## Diff

```
 mini_agent/toolkits/registry_builder.py |  72 +++++++++++++++
 tests/test_durable_workers.py           | 158 ++++++++++++++++++++++++++++++++
 2 files changed, 230 insertions(+)
```

## Notes

- No push or commit performed.
- Does not run or execute tasks, create worktrees, or change task status transition rules.
- Claim event payload contains only safe metadata: `operation`, `task_id`, `worker_id_present`, `previous_worker_id_present`.
- Existing durable task and worker semantics unchanged.
