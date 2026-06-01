# Claude A Completion Report — TASK-058: Durable Task Timeline Inspection Tool v1

Status: ready for Codex review

## Review Fix

**Problem**: Event store failure path returned `事件查询失败: {e}` with raw exception text, which could leak sentinel/secret content from exception messages.

**Fix**: Changed to fixed message `事件查询失败` without exception content. Added test `test_event_store_failure_returns_safe_error` that injects a sentinel secret into the exception, verifies JSON error is returned, and asserts the sentinel does not appear in output.

## Summary

Added read-only `get_durable_task_timeline` registry tool that returns a safe chronological (oldest-first) event timeline for a durable task, with bounded task summary and event summaries containing only key names (no raw payload values).

## Changes

### `mini_agent/toolkits/registry_builder.py`
- Added `_get_durable_task_timeline_json(task_id, limit=50)`:
  - Validates task_id exists; returns JSON error if not found
  - `limit` bounded to 1..200; non-integer returns JSON error
  - Fetches events via `DurableEventStore.list_events(task_id=...)`, reverses to chronological oldest-first
  - Returns bounded task summary: `task_id`, `status`, `event_count`, `returned_event_count`, `checkpoint_count`, `trace_ref_count`, `worker_id_present`
  - Returns event summaries with safe metadata only: `event_id`, `event_type`, `created_at`, `source`, `severity`, `checkpoint_id`, `checkpoint_id_present`, `trace_id_present`, `worker_id_present`, `summary_present`, `payload_key_count`, `payload_keys` (sorted key names only, no values)
  - No raw goal, step text, notes, summaries, checkpoint descriptions, state_snapshot, payload values, prompts, diffs, or secrets
  - Event store failure returns bounded JSON error
  - Read-only: no task or event state mutation
  - Registered with `risk="read"` permission

### `tests/test_durable_tasks.py`
- Added `DurableTaskTimelineToolTests` class with 12 tests:
  - `test_chronological_timeline` — oldest-first ordering verified
  - `test_task_summary_fields` — all summary fields present
  - `test_event_summaries_safe` — all safe fields present on each event
  - `test_payload_keys_names_only` — keys are strings, no raw values
  - `test_limit_bounding` — limits output to requested count
  - `test_limit_clamped_to_range` — 0→1, 999→200
  - `test_non_integer_limit_returns_error`
  - `test_unknown_task_returns_error`
  - `test_no_raw_goal_step_leakage` — no sentinel goal/step/checkpoint text
  - `test_no_mutation` — task state unchanged
  - `test_checkpoint_id_only_as_safe_metadata` — checkpoint_id is safe id string

## Verification

```
$ python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 470 tests — OK

$ python3 evals/run_evals.py
202 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/toolkits/registry_builder.py |  70 +++++++++++++++
 tests/test_durable_tasks.py             | 149 ++++++++++++++++++++++++++++++++
 2 files changed, +219 lines
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- Tool is strictly read-only; no task/event state mutation.
