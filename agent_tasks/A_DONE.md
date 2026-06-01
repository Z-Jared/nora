# Claude A Completion Report — TASK-056: Durable Recovery Plan Event Logging v1

Status: ready for Codex review

## Summary

Added `RECOVERY_PLANNED` durable event type and event logging to `plan_durable_recovery`. The tool now records a bounded safe event whenever a recovery plan is generated successfully. Event logging failures do not prevent plan generation.

## Changes

### `mini_agent/durable_events.py`
- Added `RECOVERY_PLANNED = "recovery_planned"` constant
- Added to `VALID_EVENT_TYPES`

### `mini_agent/toolkits/registry_builder.py`
- Imported `RECOVERY_PLANNED`
- Added event logging to `_plan_durable_recovery_json` after plan computation:
  - `event_type`: `RECOVERY_PLANNED`
  - `task_id`: task id
  - `checkpoint_id`: selected checkpoint id when present, empty string otherwise
  - `source`: `registry`
  - `severity`: `info`
  - `summary`: `"recovery planned"`
  - Payload: `operation`, `can_resume`, `resume_policy`, `reason`, `selected_checkpoint_present`, `checkpoint_step_id`, `next_step_id`, `checkpoint_count`, `step_count`, `incomplete_step_count`, `trace_ref_count`, `worker_id_present`, `requested_checkpoint_id_present`, `requested_step_id_present`
  - Wrapped in try/except — failure does not prevent plan return
  - Error responses (unknown task/checkpoint/bad step_id) skip event logging

### `tests/test_durable_tasks.py`
- Added `DurableRecoveryPlanEventTests` class with 6 tests:
  - `test_recovery_planned_event_with_checkpoint` — event with checkpoint linkage
  - `test_recovery_planned_event_no_checkpoint` — event without checkpoint
  - `test_checkpoint_id_linked_on_event` — top-level `checkpoint_id` matches selected
  - `test_event_payload_no_raw_leakage` — no sentinel checkpoint description/state_snapshot/goal/step text
  - `test_event_failure_does_not_prevent_plan` — broken event store still returns plan
  - `test_plan_does_not_mutate_task_state` — read-only verified

## Verification

```
$ python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 458 tests — OK

$ python3 evals/run_evals.py
198 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/durable_events.py            |   2 +
 mini_agent/toolkits/registry_builder.py |  29 +++++++++
 tests/test_durable_tasks.py             | 112 ++++++++++++++++++++++++++++++++
 3 files changed, +143 lines
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- Error responses skip event logging per task spec.
- Tool remains `risk="read"`; event is audit metadata only.
