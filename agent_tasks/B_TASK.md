# Claude B Task

Owner: Claude B
Status: waiting

## Goal

TASK-055: Deterministic eval coverage for durable recovery plans.

This task is waiting for TASK-054 runtime. Do not start implementation until Codex PM explicitly assigns it after TASK-054 is approved and its runtime is visible in your CCB worktree.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-054 runtime bug.

Do not call external APIs. Do not start real agents or terminals.

Planned deterministic eval coverage:

1. Recovery plan basics:
   - Create a durable task.
   - Add checkpoints.
   - Call `plan_durable_recovery`.
   - Verify selected checkpoint, resume_policy, next_step_id, counts, and can_resume.

2. Selection and fallback:
   - Explicit checkpoint_id selection.
   - step_id selection.
   - Missing step checkpoint fallback.
   - No-checkpoint fallback.
   - Unknown task/checkpoint and bad step_id errors.

3. Safety:
   - Output does not leak raw goals, step text, notes, summaries, checkpoint descriptions, state_snapshot values, prompts, diffs, shell output, or secret-like sentinels.

4. Compatibility:
   - Existing durable task registry tools still work after recovery-plan errors/no-ops.
   - Recovery planning does not mutate task state.

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
