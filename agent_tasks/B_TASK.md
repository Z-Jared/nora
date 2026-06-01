# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-053: Deterministic eval coverage for durable checkpoint controls.

Add offline deterministic eval coverage for TASK-052 so Nora's explicit durable checkpoint controls are regression-tested without external APIs or real worker processes.

## Scope

Edit `evals/run_evals.py` only unless you discover a real TASK-052 runtime bug. TASK-052 runtime was present in the worker worktree for eval development.

Do not call external APIs. Do not start real agents or terminals.

Add deterministic eval cases covering:

1. Checkpoint basics:
   - Create a durable task.
   - Call `add_durable_checkpoint`.
   - Checkpoint count increments.
   - Returned JSON is bounded and includes task_id/checkpoint_id/step_id/count/presence flags only.

2. Step and store consistency:
   - Matching step gets `checkpoint_ref`.
   - Existing checkpoints and trace refs are preserved.
   - Invalid/bad `step_id` is bounded or rejected deterministically.
   - Unknown task ids return a JSON error.

3. Event coverage:
   - `CHECKPOINT_ADDED` event is recorded with checkpoint_id and safe metadata.
   - Event payload does not include raw goal, raw step text, raw summaries, prompt text, diffs, shell output, or secrets.

4. Safety and failure isolation:
   - Output does not leak raw task goals, full steps, prompts, raw summaries, or secret-like sentinels.
   - Broken event store does not prevent checkpoint creation.
   - Existing durable task registry tools still work after checkpoint errors/no-ops.

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
