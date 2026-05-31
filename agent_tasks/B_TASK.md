# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-031: eval coverage for durable task worker assignment.

TASK-028 added worker ownership metadata to durable task registry tools. Add deterministic offline eval coverage so worker assignment behavior and worker-linked task events remain stable.

## Scope

Edit `evals/run_evals.py` only unless you discover a real runtime bug. If you find a runtime bug, stop and report it in `agent_tasks/B_DONE.md` instead of fixing runtime code in this task.

Add eval cases covering:

1. Worker assignment basics:
   - `create_durable_task(worker_id=...)` stores worker ownership.
   - `assign_durable_task` sets worker ownership.
   - Empty/whitespace assignment clears worker ownership.
   - `list_durable_tasks` includes `worker_id`.

2. Worker-linked events:
   - Task action events include top-level `worker_id` after create/update/retry/delete when assigned.
   - Assignment emits a safe event with `operation="assign"`.
   - `list_durable_events(worker_id=...)` can query worker-linked events.

3. Safety:
   - Use sentinel goal/step/secret values.
   - Assert sentinels are absent from assignment events and `list_durable_events` output.

4. Failure isolation:
   - Broken event store must not change `assign_durable_task` behavior.

Keep evals offline and deterministic. Do not call live LLM APIs.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_durable_tasks tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
