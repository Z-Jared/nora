# Claude B Task

Owner: Claude B
Status: waiting

## Goal

TASK-059: Deterministic eval coverage for durable task timeline.

This task is waiting for TASK-058 runtime. Do not start implementation until Codex PM explicitly assigns it after TASK-058 is approved and its runtime is visible in your CCB worktree.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-058 runtime bug.

Do not call external APIs. Do not start real agents or terminals.

Planned deterministic eval coverage:

1. Timeline basics:
   - Create a durable task.
   - Generate task/create/checkpoint/recovery events.
   - Call `get_durable_task_timeline`.
   - Verify chronological ordering, task summary counts, and bounded event summaries.

2. Linkage and limit behavior:
   - checkpoint_id linkage appears as safe id metadata.
   - payload_keys lists safe key names only.
   - limit bounds are deterministic.
   - Unknown task and bad limit return JSON errors.

3. Safety:
   - Timeline output does not leak raw goals, step text, notes, summaries, checkpoint descriptions, state_snapshot values, raw payload values, prompt text, diffs, shell output, env vars, request strings, or secret-like sentinels.

4. Compatibility:
   - Timeline inspection does not mutate task or event state.
   - Existing durable task/event registry tools still work after timeline errors/no-ops.

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
