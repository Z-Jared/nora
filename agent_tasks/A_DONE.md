# Claude A Completion Report — TASK-032: Durable Worker Heartbeat and Offline Lifecycle v1

Status: ready for Codex review

## Summary

Added heartbeat and stale→offline lifecycle to the durable worker registry. Workers can be touched (heartbeat) and stale workers can be automatically marked offline without mutating durable task ownership.

## Changes

### `mini_agent/durable_workers.py`
- Added `mark_stale_workers_offline(max_age_seconds: int = 300) -> list[DurableWorker]` method
- Iterates all workers, finds those with `last_seen_at` older than threshold and status != offline
- Sets `status="offline"` and updates `updated_at`; preserves `last_seen_at` (last actual heartbeat)
- Does not mutate durable tasks or clear task ownership

### `mini_agent/toolkits/registry_builder.py`
- Added `touch_worker(worker_id)` registry tool — updates `last_seen_at`, returns JSON
- Added `mark_stale_workers_offline(max_age_seconds=300)` registry tool — returns JSON summary of changed workers
- Both handle empty/unknown IDs and invalid thresholds as JSON errors

### `tests/test_durable_workers.py`
- Added `DurableWorkerHeartbeatTests` class with 8 tests:
  - `test_sqlite_touch_updates_last_seen_and_updated`
  - `test_jsonl_touch_updates_last_seen_and_updated`
  - `test_sqlite_stale_workers_become_offline`
  - `test_jsonl_stale_workers_become_offline`
  - `test_fresh_workers_not_marked_offline`
  - `test_already_offline_workers_not_returned_as_changed`
  - `test_mark_offline_preserves_current_task_id`
  - `test_touch_unknown_returns_none`
- Added registry tool tests to `RegistryWorkerToolTests`:
  - `test_touch_worker_returns_json`
  - `test_touch_worker_unknown_returns_error`
  - `test_touch_worker_empty_id_returns_error`
  - `test_mark_stale_workers_offline_returns_json`
  - `test_mark_stale_workers_offline_invalid_threshold_returns_error`
  - `test_mark_offline_does_not_mutate_durable_task`

## Verification

```
$ python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 441 tests — OK

$ python3 evals/run_evals.py
143 passed, 0 failed

$ python3 -m unittest discover -s tests
Ran 1309 tests — OK

$ git diff --check
OK
```

## Diff

```
 mini_agent/durable_workers.py           |  18 ++++
 mini_agent/toolkits/registry_builder.py |  50 ++++++++++
 tests/test_durable_workers.py           | 166 ++++++++++++++++++++++++++++++++
 3 files changed, 234 insertions(+)
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- Does not implement scheduling, worktree creation, or task reassignment.
- Existing durable task worker assignment semantics unchanged.
