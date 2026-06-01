# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-065: Deterministic eval coverage for worker workspace sandbox guard.

Codex PM approved this task after review. TASK-064 runtime is integrated locally.

## Scope

Edit `evals/run_evals.py` only unless a real TASK-064 runtime bug is discovered. Do not call external APIs. Do not start real agents or terminals.

Deterministic offline eval coverage:

1. Valid sandbox paths:
   - `get_worker_workspace` returns bounded lease metadata
   - `validate_worker_workspace_path` accepts absolute paths inside the workspace
   - workspace root itself is valid

2. Rejection cases:
   - path traversal that escapes workspace
   - absolute path escape outside workspace
   - unknown worker
   - worker with no lease
   - task mismatch
   - empty path
   - offline worker with stale current_task_id and lease
   - idle worker with stale current_task_id and lease

3. Safety and compatibility:
   - outputs do not leak raw task goal, steps, prompts, shell output, diffs, env vars, or secrets
   - sandbox guard errors do not break worker/task list/get tools
   - claim still works after sandbox guard errors
   - post-claim validation uses an absolute path inside the claimed workspace and strictly asserts `valid is True`

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
