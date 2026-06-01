# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-049: Deterministic eval coverage for durable worker auto-dispatch.

Add offline eval coverage for TASK-048 so Nora can automatically assign pending durable tasks to available workers safely and deterministically.

## Scope

Edit `evals/run_evals.py` only unless you discover a real TASK-048 runtime bug. If TASK-048 runtime is not present yet, wait or write `agent_tasks/B_DONE.md` as blocked by missing runtime.

Do not call external APIs. Do not start real agents or terminals.

Add deterministic eval cases covering:

1. Dispatch basics:
   - Register idle workers.
   - Create pending unassigned durable tasks.
   - `dispatch_durable_tasks` assigns oldest tasks to available workers.
   - Returned JSON is bounded and includes assignment count/ids.

2. Limits and exclusions:
   - `max_assignments` is respected and bounded.
   - Running/assigned/paused/offline workers do not receive new tasks.
   - Existing assigned tasks are not reassigned.
   - No idle workers or no pending tasks returns an empty assignment result, not an error.

3. State consistency:
   - Task `worker_id` is updated.
   - Worker status/current task is updated consistently.
   - Task status behavior remains compatible with existing claim semantics.

4. Safety and failure isolation:
   - Output does not leak raw task goals, full steps, prompts, or secret-like sentinels.
   - Broken event store does not prevent dispatch.
   - Existing worker/task registry tools still work after dispatch errors/no-ops.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
