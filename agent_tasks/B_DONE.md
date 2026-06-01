# Claude B Completion Report

Task: TASK-061 — Deterministic eval coverage for worker workspace lease
Status: ready for Codex review

## Summary

Added 5 deterministic offline eval cases for `prepare_worker_workspace` / `release_worker_workspace` (TASK-060 runtime).

- **workspace_lease_happy_path** — Register worker, create task, assign, set worker to assigned+current_task_id, call `prepare_worker_workspace`. Verifies lease_id format (`wlease_` prefix), worker_id, task_id, workspace_path exists on disk, created_at present. Bounded output (no goal/steps/secrets). Release returns `released=True` with matching lease_id.

- **workspace_lease_validation_errors** — Unknown worker → error. Unknown task → error. Offline worker → error (contains "离线"). Idle worker with matching task.worker_id but no current_task_id → error (contains "空闲"). Worker current_task_id mismatch → error. Task.worker_id mismatch → error.

- **workspace_lease_idempotency_uniqueness** — Same worker+task already has lease → error with `existing_lease_id`. Same task already leased (via real registry call with second worker reassigned to same task) → error with `existing_lease_id` matching first lease. Release removes lease (confirmed via store). Release with no lease returns `released=False`. After release, re-prepare succeeds with valid lease_id format.

- **workspace_lease_safety** — No raw goal/steps/secrets in prepare output. No raw goal/secrets in workspace_prepared event payload. Event payload only contains allowed keys (operation/lease_id/worker_id/task_id). No raw goal/secrets in workspace_released event. Release event payload only contains allowed keys (operation/lease_id/worker_id). mkdir failure (mocked OSError) returns error and no lease created.

- **workspace_lease_failure_isolation_compatibility** — Broken event store doesn't prevent prepare/release. After errors, get_worker/get_durable_task/list_workers/list_durable_tasks still work. Validation errors don't break subsequent valid operations.

## Review Fix (REVIEW.md Must Fix #1)

Strengthened `eval_workspace_lease_idempotency_uniqueness()` to exercise the real task-level duplicate lease registry branch:
- Worker1 prepares task1 → `lease_id_1`
- Task1 is reassigned to worker2 via `ts.assign_worker(tid1, "w_dup2")`
- Worker2 status set to `assigned` with `current_task_id=tid1`
- `prepare_worker_workspace(worker_id="w_dup2", task_id=tid1)` called
- Asserts `error` and `existing_lease_id == lease_id_1`

Also cleaned up: removed unused `task_id_override` helper parameter and unused `tid_another` variable.

## Diff

```text
 evals/run_evals.py | 312 ++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 311 insertions(+), 1 deletion(-)
```

## Tests

```text
python3 evals/run_evals.py
211 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 553 tests in 12.001s — OK

git diff --check
OK
```

## Notes

- No runtime code changed (TASK-060 was already complete).
- No commit or push performed.
- Added WORKSPACE_PREPARED and WORKSPACE_RELEASED to eval imports.
- Known issues: none.
