# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-057: Deterministic eval coverage for recovery-plan events.

TASK-056 runtime is approved and present for eval development.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-056 runtime bug.

Do not call external APIs. Do not start real agents or terminals.

Planned deterministic eval coverage:

1. Recovery-plan event basics:
   - Create a durable task.
   - Add checkpoints.
   - Call `plan_durable_recovery`.
   - Verify `RECOVERY_PLANNED` event is recorded with checkpoint_id linkage and safe metadata.

2. Selection and fallback events:
   - Explicit checkpoint_id selection event.
   - step_id selection event.
   - No-checkpoint fallback event.
   - Terminal status event.

3. Safety:
   - Event payload/serialized event does not leak raw goals, step text, notes, summaries, checkpoint descriptions, state_snapshot values, prompt text, diffs, shell output, env vars, request strings, or secret-like sentinels.

4. Compatibility:
   - Broken event store does not prevent recovery planning.
   - Existing durable task registry tools still work after recovery planning.
   - Recovery planning still does not mutate task state.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files and explain why in `agent_tasks/B_DONE.md`.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
