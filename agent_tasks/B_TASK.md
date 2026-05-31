# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-035: eval coverage for durable worker heartbeat/offline lifecycle.

TASK-032 added `touch_worker` and `mark_stale_workers_offline`. Add deterministic offline eval coverage so worker heartbeat, stale detection, safety, and failure isolation remain stable.

## Scope

Edit `evals/run_evals.py` only unless you discover a real runtime bug. If you find a runtime bug, stop and report it in `agent_tasks/B_DONE.md` instead of fixing runtime code in this task.

Add eval cases covering:

1. Heartbeat basics:
   - `touch_worker(worker_id=...)` updates `last_seen_at` for an existing worker.
   - Unknown/empty worker IDs return JSON errors.

2. Offline lifecycle:
   - A stale worker is marked `offline`.
   - A fresh worker is not marked offline.
   - An already-offline worker is not counted as newly changed.
   - Marking offline preserves `current_task_id`.

3. Task isolation:
   - Marking a worker offline does not mutate durable task ownership or task status.

4. Safety:
   - Use sentinel worker role/path/task values and task goal/step values.
   - Assert heartbeat/offline outputs and events do not leak raw task goal, steps, env vars, prompts, or unrelated event payloads.

5. Failure isolation:
   - Broken durable event store must not change `touch_worker` or `mark_stale_workers_offline` behavior.

Keep evals offline and deterministic. Do not call live LLM APIs.

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
