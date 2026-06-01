# Claude A Completion Report — TASK-054: Durable Recovery Plan Tool v1

Status: ready for Codex review

## Review Fix

**Problem 1**: `resume_policy` always returned `from_step` even when a checkpoint was selected. Per TASK-054 semantics, checkpoint-selected plans should use `from_checkpoint`.

**Fix**: Changed `resume_policy` logic: returns `from_checkpoint` when a checkpoint is selected (latest, explicit, or step-based); returns `task.resume_policy` or `from_step` only for no-checkpoint fallback.

**Problem 2**: No tests asserted `resume_policy`.

**Fix**: Added 3 tests: `test_resume_policy_from_checkpoint_when_latest_selected`, `test_resume_policy_from_checkpoint_when_explicit_id`, `test_resume_policy_from_step_when_no_checkpoint`.

**Problem 3**: No test verifying checkpoint description/state_snapshot sentinel not leaked.

**Fix**: Added `test_checkpoint_description_and_snapshot_not_leaked` — injects sentinel text into checkpoint description and nested state_snapshot, verifies absent from `plan_durable_recovery` output.

## Summary

Added read-only `plan_durable_recovery` registry tool that inspects durable task state and checkpoints to compute a safe recovery plan. The tool does not mutate task state, execute recovery, start workers, or expose raw goal/step/note/summary/checkpoint text.

## Changes

### `mini_agent/toolkits/registry_builder.py`
- Added `_plan_durable_recovery_json(task_id, checkpoint_id="", step_id="")`:
  - **Checkpoint selection**: explicit `checkpoint_id` → step-based latest → overall latest → none
  - **`next_step_id` computation**: prefers checkpoint step if not done/skipped, else first incomplete step, else `current_step`
  - **`can_resume`**: false for `completed`/`cancelled`, true for `pending`/`running`/`paused`/`blocked`/`failed`
  - **Reason labels**: `checkpoint_selected`, `step_checkpoint_missing`, `no_checkpoint`, `terminal_status`, `all_steps_done`
  - Non-integer `step_id` returns JSON error
  - Unknown `checkpoint_id` returns JSON error
  - Read-only: no task/step state mutation
  - Bounded output: only safe metadata fields, no raw goal/step/note/summary/checkpoint description/state_snapshot
  - Registered with `risk="read"` permission

### `tests/test_durable_tasks.py`
- Added `DurableRecoveryPlanToolTests` class with 19 tests:
  - `test_latest_checkpoint_selected` — auto-selects most recent checkpoint
  - `test_explicit_checkpoint_id_selection` — selects exact checkpoint by id
  - `test_step_id_selection` — selects checkpoint for given step
  - `test_step_id_missing_checkpoint` — returns `step_checkpoint_missing` reason
  - `test_no_checkpoint_fallback` — returns `no_checkpoint` reason with null checkpoint_id
  - `test_completed_task_can_resume_false` — terminal status
  - `test_cancelled_task_can_resume_false` — terminal status
  - `test_failed_task_can_resume_true` — failed is resumable
  - `test_unknown_task_returns_error`
  - `test_unknown_checkpoint_returns_error`
  - `test_non_integer_step_id_returns_error`
  - `test_no_goal_or_step_text_leakage` — output safety
  - `test_no_mutation_of_task_state` — read-only verification
  - `test_next_step_prefers_checkpoint_step_when_not_done`
  - `test_next_step_skips_done_steps`

## Verification

```
$ python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 452 tests — OK

$ python3 evals/run_evals.py
194 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/toolkits/registry_builder.py | 114 +++++++++++++++++++-
 tests/test_durable_tasks.py             | 185 ++++++++++++++++++++++++++++++++
 2 files changed, +298/-1 lines
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- Tool is strictly read-only — no task mutation, no worker execution, no model calls.
