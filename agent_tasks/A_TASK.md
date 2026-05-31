# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-032: durable worker heartbeat and offline lifecycle v1.

Nora now has a durable worker registry, but worker liveness is only implicit. Add a small heartbeat/offline lifecycle so the runtime can record that a worker is still alive and mark stale workers as offline without mutating durable task ownership.

## Scope

Build narrowly on `mini_agent/durable_workers.py` and `mini_agent/toolkits/registry_builder.py`.

1. Extend durable worker storage:
   - Keep the existing `touch(worker_id)` behavior, but ensure it is covered by tests for SQLite and JSONL.
   - Add a store method to mark stale workers offline, for example `mark_stale_workers_offline(max_age_seconds: int) -> list[DurableWorker]`.
   - A worker is stale when `last_seen_at` is older than the threshold and status is not already `offline`.
   - Mark stale workers with `status="offline"` and update `updated_at`.
   - Do not change `last_seen_at` when marking offline; it should remain the last actual heartbeat timestamp.
   - Do not mutate durable tasks or clear task ownership from durable tasks.

2. Add registry tools:
   - `touch_worker(worker_id)` updates `last_seen_at` for an existing worker and returns JSON.
   - `mark_stale_workers_offline(max_age_seconds=300)` returns a bounded JSON summary of workers that changed status.
   - Empty/unknown worker IDs should return JSON errors, not raise.
   - Invalid threshold values should return JSON errors, not raise.

3. Safety and compatibility:
   - Keep worker records as metadata only; do not expose env vars, prompts, secrets, shell output, or raw tool data.
   - Do not implement scheduling, worktree creation, or task reassignment in this task.
   - Existing durable task worker assignment semantics must stay unchanged.

## Suggested Tests

Add or extend focused tests in `tests/test_durable_workers.py`:

1. SQLite `touch` updates `last_seen_at` and `updated_at`.
2. JSONL `touch` updates `last_seen_at` and `updated_at`.
3. SQLite stale workers become `offline`; fresh workers do not.
4. JSONL stale workers become `offline`; fresh workers do not.
5. Already-offline workers are not returned as newly changed.
6. Registry `touch_worker` and `mark_stale_workers_offline` return expected JSON.
7. Registry invalid inputs return JSON errors.
8. Marking a worker offline does not mutate the durable task that references that worker.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared registry wiring broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
