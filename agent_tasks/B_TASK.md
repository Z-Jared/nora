# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-033: eval coverage for durable worker registry tools.

TASK-030 added the durable worker registry and registry tools. Add deterministic offline eval coverage so worker registration, lookup, listing, status updates, safety, and failure isolation stay stable.

## Scope

Edit `evals/run_evals.py` only unless you discover a real runtime bug. If you find a runtime bug, stop and report it in `agent_tasks/B_DONE.md` instead of fixing runtime code in this task.

Add eval cases covering:

1. Worker registry basics:
   - `register_worker` stores `worker_id`, `role`, `workspace_path`, and default `status`.
   - Re-registering an existing worker updates role/workspace metadata without creating a duplicate.
   - `get_worker` returns the registered worker.
   - `list_workers` includes registered workers.

2. Worker status updates:
   - `update_worker_status` sets `status` and `current_task_id`.
   - Updating back to `idle` can clear `current_task_id`.
   - Unknown worker returns a JSON error.
   - Invalid status returns a JSON error.

3. Safety:
   - Use sentinel role/path/current_task values that look secret-like.
   - Assert worker registry outputs do not include environment variables, raw prompts, durable task goals, or unrelated event payloads.
   - Do not add live LLM calls.

4. Failure isolation:
   - Worker registry operations should still work if the durable event store is replaced with a broken object, because worker registry tools should not depend on event logging.

Keep evals offline and deterministic.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_durable_tasks tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
