# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-063: Deterministic eval coverage for worker workspace integration.

Codex PM approved this task after review. TASK-062 runtime is integrated locally.

## Scope

Edit `evals/run_evals.py` only unless a real TASK-062 runtime bug is discovered. Do not call external APIs. Do not start real agents or terminals.

Deterministic offline eval coverage:

1. Claim/dispatch workspace integration:
   - claim auto-prepares a workspace lease
   - dispatch auto-prepares a workspace lease per assignment
   - workspace directories exist when preparation succeeds

2. Reuse and uniqueness:
   - same worker claiming the same task reuses the same lease
   - multiple dispatched workers receive unique leases
   - offline/idle/mismatch cases do not create invalid workspace leases

3. Failure isolation:
   - workspace prepare failure does not block claim
   - workspace prepare failure does not block dispatch
   - existing list/get worker/task tools still work after workspace failures

4. Safety and events:
   - workspace sub-dict does not leak raw goal, steps, prompts, shell output, diffs, env vars, or secrets
   - `WORKSPACE_PREPARED` events contain safe metadata only
   - no pending tasks means dispatch returns no workspace activity

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
git diff --check
```

## Completion Report

Written in `agent_tasks/B_DONE.md`.

Do not commit or push.
