# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-068: Worker workspace write tools v1.

Nora can now prepare active worker workspace leases and expose read-only worker-scoped file inspection/preview tools. The next worker-isolation step is allowing a worker to actually modify files inside its leased workspace only, without touching the project root or other workers' workspaces.

## Scope

Add minimal registry-level write tools. Do not implement shell execution, process isolation, Docker, git worktrees, project-root merge, patch queues, UI changes, or model routing in this task.

1. Add worker workspace write tools near the existing workspace lease / file inspection section in `mini_agent/toolkits/registry_builder.py`:
   - `write_worker_workspace_file(worker_id, task_id, path, content, reason="")`
   - `replace_worker_workspace_file(worker_id, task_id, path, old_text, new_text, reason="")`
   - `apply_worker_workspace_patch(worker_id, task_id, patch, reason="")`

2. Reuse existing worker workspace validation:
   - Worker must exist.
   - Worker must not be offline or idle.
   - `worker.current_task_id == task_id`.
   - Task must exist.
   - `task.worker_id == worker_id`.
   - Active lease must exist and belong to the task.
   - Paths must resolve inside the lease workspace root.
   - Sensitive names/dirs such as `.env`, `.git`, `data`, `logs`, `__pycache__`, `.pytest_cache` must be rejected.
   - Symlink escape and symlink-to-denied-dir behavior must stay consistent with read/preview/list.

3. Write behavior:
   - Writes may create parent directories inside the workspace.
   - Replace requires `old_text` to be non-empty and present.
   - Patch applies only to files inside the worker workspace.
   - Patch format should be unified diff using project workspace helpers where practical, but paths must be scoped to lease root, not project root.
   - All content/result sizes must stay bounded by existing workspace file byte limits.
   - Binary/oversized/unsafe files return bounded JSON errors.
   - Do not write outside the active workspace under any condition.

4. Output and event safety:
   - All tools return JSON.
   - Return safe metadata: path, bytes before/after, operation, changed/created flags, lease_id, worker_id, task_id.
   - Do not return raw task goal, steps, prompts, shell output, env vars, request strings, secrets, or full patch/content except for bounded safe snippets if already established locally.
   - Record safe durable file-edit style events if the current event store pattern supports it; event failure must not block the write.
   - Do not mutate durable task/worker/lease ownership/status.

5. Compatibility:
   - Preserve existing behavior of workspace lease tools, file inspection tools, sandbox guard tools, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` and/or workspace tests covering:

- Writing a new file inside a prepared worker workspace.
- Replacing text inside a workspace file.
- Applying a patch inside a workspace file.
- Relative and absolute paths inside workspace accepted.
- Traversal, absolute escape, symlink escape, symlink to denied dirs, `.env`, `.git`, `logs`, and `data` rejected.
- Unknown worker, no lease, task mismatch, offline/idle worker rejected.
- Oversized content/file and binary file handling.
- No raw task goal/steps/secret sentinel leak in outputs/events.
- Writes mutate files only inside the lease workspace and do not mutate task/worker/lease state.
- Existing read/list/preview tools still work after write errors and successful writes.

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
