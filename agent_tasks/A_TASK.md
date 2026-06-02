# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-066: Worker workspace file inspection tools v1.

Nora now prepares workspace leases for durable workers and has read-only sandbox guard tools. The next worker-isolation step is to expose worker-scoped file inspection and write-preview tools that operate only inside the active workspace lease for the worker's current task.

## Scope

Add minimal registry-level tools. Do not implement shell execution, process isolation, Docker, git worktrees, patch queues, real file writes, or UI changes in this task.

1. Add worker workspace file tools near the existing workspace lease / sandbox guard section in `mini_agent/toolkits/registry_builder.py`:
   - `list_worker_workspace_files(worker_id, task_id, max_files=50)`
   - `read_worker_workspace_file(worker_id, task_id, path)`
   - `preview_worker_workspace_write(worker_id, task_id, path, content, context_lines=3)`

2. Reuse the existing lease validation semantics:
   - Worker must exist.
   - Worker must not be offline or idle.
   - `worker.current_task_id == task_id`.
   - Task must exist.
   - `task.worker_id == worker_id`.
   - Active lease must exist and belong to the task.

3. Path handling:
   - Relative `path` values are resolved under the lease workspace root.
   - Absolute `path` values are allowed only if they resolve inside the lease workspace root.
   - Path traversal or symlink/absolute escapes must return bounded JSON errors.
   - Empty path should return a JSON error for read/preview.
   - Reuse the existing workspace file safety rules where practical, including denial of sensitive names such as `.env` and `.git`.

4. Output shape and safety:
   - All tools return JSON.
   - `list_worker_workspace_files` returns bounded relative file paths only.
   - `read_worker_workspace_file` returns bounded UTF-8 text content plus safe metadata; oversized/binary/missing/disallowed files return bounded JSON errors.
   - `preview_worker_workspace_write` returns a diff/preview only; it must not write or create files.
   - Do not return raw task goal, steps, prompts, shell output, env vars, request strings, diffs outside the requested preview, or secret-like task data.
   - Do not mutate durable task, worker, lease, or event state.

5. Permissions and compatibility:
   - Register these as read-risk tools because this task only inspects files and previews writes.
   - Preserve existing behavior of workspace lease, sandbox guard, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` and/or workspace tests covering:

- Listing files inside a prepared worker workspace with bounded relative paths.
- Reading a file inside the workspace.
- Previewing a write without mutating the file system.
- Relative path inside workspace accepted.
- Absolute path inside workspace accepted.
- Traversal and absolute escape rejected.
- Missing worker, no lease, task mismatch, offline/idle worker rejected.
- Sensitive paths such as `.env` / `.git` rejected.
- Safe output does not leak task goal/steps or secret-like sentinels.
- Read/list/preview do not mutate task/worker/lease/event state.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared workspace helpers broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
