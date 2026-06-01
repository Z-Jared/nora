# Claude A Completion Report — TASK-052: Durable Checkpoint Control Tools v1

Status: ready for Codex review

## Review Fix

**Problem**: `step_id="bad"` caused `int(step_id)` to raise `ValueError`, crashing the registry tool.

**Fix**: Wrapped `step_id` parsing in try/except — non-integer values now return JSON `{"error": "step_id 必须为整数: ..."}` and leave task checkpoints unchanged. Negative integers still clamp to 0.

**New test**: `test_non_integer_step_id_returns_error` — verifies JSON error response and that no checkpoint is created.

## Summary

Added `add_durable_checkpoint` registry tool that creates safe, inspectable checkpoints on demand. The tool creates bounded state snapshots with safe metadata only, updates step `checkpoint_ref` when applicable, logs `CHECKPOINT_ADDED` events, and returns bounded JSON without exposing raw goal, step text, prompts, or sensitive content.

## Changes

### `mini_agent/toolkits/registry_builder.py`
- Added `_add_durable_checkpoint_json(task_id, step_id=0, description="", state_summary="")`:
  - Validates task_id exists, returns JSON error if not found
  - Bounds `step_id` to integer >= 0
  - Creates `state_snapshot` with safe metadata only: `task_status`, `current_step`, `step_id`, `description_present`, `state_summary_present`
  - Does NOT store raw goal, step text, description text, state_summary text, prompts, diffs, or secrets
  - Updates `step.checkpoint_ref` if `step_id` matches an existing step
  - Records `CHECKPOINT_ADDED` event with safe metadata and `checkpoint_id`
  - Returns bounded JSON: `task_id`, `checkpoint_id`, `step_id`, `checkpoint_count`, `description_present`, `state_summary_present`
  - Event logging failure does not prevent checkpoint creation

### `tests/test_durable_tasks.py`
- Added `DurableCheckpointToolTests` class with 12 tests:
  - `test_successful_checkpoint_creation` — full happy path
  - `test_step_checkpoint_ref_updated` — step ref linking
  - `test_step_checkpoint_ref_not_updated_for_nonexistent_step` — no ref for invalid step
  - `test_unknown_task_returns_error`
  - `test_step_id_bounded_to_non_negative` — negative step_id clamped to 0
  - `test_multiple_checkpoints_increment` — checkpoint IDs and counts
  - `test_no_goal_or_step_text_leakage` — output safety
  - `test_checkpoint_emits_event` — event logging verified
  - `test_event_failure_does_not_prevent_checkpoint` — failure isolation
  - `test_checkpoint_preserves_task_status` — no side effects
  - `test_state_snapshot_is_safe` — snapshot contains no raw text

## Verification

```
$ python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 433 tests — OK

$ python3 evals/run_evals.py
190 passed, 0 failed

$ git diff --check
clean

$ python3 -m unittest discover -s tests
Ran 1554 tests — OK
```

## Diff

```
 mini_agent/toolkits/registry_builder.py |  84 +++++++++++++++++++++
 tests/test_durable_tasks.py             | 126 ++++++++++++++++++++++++++++++++
 2 source files changed, +210 lines
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- Uses existing `DurableTaskStore.add_checkpoint()` — no store-level changes needed.
