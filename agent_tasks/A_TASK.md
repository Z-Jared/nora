# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-060: Worker workspace lease / isolation v1.

Codex PM approved this task after review. Integrated locally after TASK-061 eval coverage.

Nora has durable workers and auto-dispatch. The next runtime depth step was a minimal workspace lease layer so an actively assigned worker can receive an isolated workspace directory before future worker execution/sandbox work.

## Scope

Build only workspace lease / isolation v1. Do not implement worker process execution, git worktree creation, patch queues, sandbox policy, multi-agent orchestration, or broad schema redesign.

1. Add durable workspace lease storage:
   - `DurableWorkspaceLease`
   - `WorkspaceLeaseStore`
   - SQLite backend via `NoraDB`
   - JSONL fallback
   - fields: `lease_id`, `worker_id`, `task_id`, `workspace_path`, `created_at`

2. Add registry tools:
   - `prepare_worker_workspace(worker_id, task_id)`
   - `release_worker_workspace(worker_id)`

3. Prepare behavior:
   - validate worker exists
   - reject offline worker
   - reject idle worker
   - require `worker.current_task_id == task_id`
   - validate durable task exists
   - require `task.worker_id == worker_id`
   - reject duplicate lease for worker
   - reject duplicate lease for task
   - create `.workspaces/{worker_id}_{task_id}`
   - if mkdir fails, return bounded JSON error and do not persist a lease
   - emit safe `WORKSPACE_PREPARED` event

4. Release behavior:
   - validate worker exists
   - return `released: false` when no lease exists
   - delete only the lease record, not the filesystem directory
   - emit safe `WORKSPACE_RELEASED` event

5. Safety and compatibility:
   - output only bounded metadata
   - do not leak task goal, steps, notes, prompts, shell output, diffs, env vars, or secrets
   - event-store failure must not block prepare/release
   - existing worker/task/event tools must remain compatible

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Completion Report

Written in `agent_tasks/A_DONE.md`.

Do not commit or push.
