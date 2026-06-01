# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-061: Deterministic eval coverage for worker workspace lease.

Codex PM approved this task after review. TASK-060 runtime is integrated locally.

## Scope

Edit `evals/run_evals.py` only unless a real TASK-060 runtime bug is discovered. Do not call external APIs. Do not start real agents or terminals.

Deterministic offline eval coverage:

1. Happy path:
   - register worker
   - create durable task
   - assign task to worker
   - set worker `assigned/current_task_id`
   - call `prepare_worker_workspace`
   - verify lease id format, worker/task ids, created_at, directory exists
   - call `release_worker_workspace`

2. Validation and uniqueness:
   - unknown worker
   - unknown task
   - offline worker
   - idle worker with matching `task.worker_id`
   - worker `current_task_id` mismatch
   - task worker mismatch
   - duplicate lease for same worker
   - duplicate lease for same task through real registry call with second active worker

3. Safety:
   - bounded outputs
   - no raw goal, steps, prompts, shell output, diffs, env vars, or secrets
   - event payload contains only safe metadata
   - mkdir failure returns error and creates no lease

4. Compatibility:
   - broken event store does not block prepare/release
   - errors do not break existing worker/task list/get tools

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
