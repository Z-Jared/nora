# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-064: Worker workspace sandbox guard v1.

Codex PM approved this task. TASK-060 workspace lease runtime, TASK-061 eval coverage, and TASK-062 workspace integration into claim/dispatch are already integrated.

Nora can create durable worker workspace leases and automatically prepare them during claim/dispatch. The next sandbox step is ensuring that worker file/command operations can only target paths within their active workspace lease directory.

## Scope

Add minimal sandbox guard tools at the registry/toolkit layer. Do not implement real process isolation, Docker, git worktrees, patch queues, or UI changes.

1. Shared validation helper:
   - `_resolve_and_validate_lease(worker_id, task_id)` returns `(lease, None)` or `(None, error_dict)`
   - Validates: worker exists, worker is not offline or idle, `worker.current_task_id == task_id`, task exists, `task.worker_id == worker_id`, lease exists, `lease.task_id == task_id`

2. Read-only tools:
   - `get_worker_workspace(worker_id, task_id)` — returns lease info or error
   - `validate_worker_workspace_path(worker_id, task_id, path)` — validates path is within workspace
   - Both registered with `risk="read"` permission

3. Path validation:
   - Uses `Path.resolve()` to normalize `..`, symlinks, and relative paths
   - Checks `resolved.relative_to(ws_root.resolve())` to ensure containment
   - Path traversal, absolute path escape, no lease, worker/task mismatch all return bounded JSON error

4. Safety:
   - Output does not leak raw task goal, steps, prompts, shell output, diffs, env vars, or secrets
   - Tools are read-only — validate paths but do not create files
   - Preserve existing workspace lease, claim, dispatch, and all other registry tools

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 -m unittest discover -s tests
python3 evals/run_evals.py
git diff --check
```

## Completion Report

Written in `agent_tasks/A_DONE.md`.

Do not commit or push.
