# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-051: Deterministic eval coverage for durable lifecycle controls.

Add offline deterministic eval coverage for TASK-050 so Nora's explicit pause/resume/cancel durable task lifecycle tools are regression-tested without external APIs or real worker processes.

## Scope

Edit `evals/run_evals.py` only unless you discover a real TASK-050 runtime bug. If TASK-050 runtime is not present yet in your worktree, write `agent_tasks/B_DONE.md` as blocked by missing runtime and do not invent a separate implementation.

Do not call external APIs. Do not start real agents or terminals.

Add deterministic eval cases covering:

1. Lifecycle basics:
   - Create a durable task.
   - Transition it to `running`.
   - `pause_durable_task` moves it to `paused`.
   - `resume_durable_task` moves it back to `running`.
   - `cancel_durable_task` moves it to `cancelled`.
   - Returned JSON is bounded and includes task id/status/previous status only.

2. Invalid transitions and not-found behavior:
   - Pause from `pending` returns an error.
   - Resume from `pending` returns an error.
   - Cancel from terminal states returns an error.
   - Unknown task ids return a JSON error.
   - Existing `retry_durable_task` semantics are not changed.

3. Worker consistency:
   - A running task assigned to a worker pauses the worker to `paused` if `current_task_id` matches.
   - Resuming that task moves a non-offline matching worker to `running`.
   - Cancelling that task releases the matching worker to `idle` with no `current_task_id`.
   - Offline or unrelated workers are not overwritten.

4. Safety and failure isolation:
   - Output does not leak raw task goals, full steps, prompts, raw reasons, or secret-like sentinels.
   - Durable events for pause/resume/cancel contain safe metadata only.
   - Broken event store does not prevent lifecycle operations.
   - Existing durable task and worker registry tools still work after lifecycle errors/no-ops.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_durable_workers tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files and explain why in `agent_tasks/B_DONE.md`.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
