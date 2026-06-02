# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-070: Worker workspace change summary / patch export tools v1.

Nora can now prepare worker workspace leases, inspect files, and let a worker write/replace/patch files inside only its leased workspace. The next worker-isolation step is giving Codex PM a safe, read-only way to inspect what a worker changed before any future merge workflow.

Add minimal registry-level read tools that compare a worker workspace against the project root and export bounded review metadata/patches. Do not implement project-root merge, patch apply to project root, git worktrees, shell execution, process isolation, Docker, UI changes, or model routing in this task.

## Scope

1. Add worker workspace change export tools near the existing worker workspace file inspection/write section in `mini_agent/toolkits/registry_builder.py`:
   - `summarize_worker_workspace_changes(worker_id, task_id, max_files=50)`
   - `export_worker_workspace_patch(worker_id, task_id, path="", max_files=50, context_lines=3)`

2. Reuse existing worker workspace validation:
   - Worker must exist.
   - Worker must not be offline or idle.
   - `worker.current_task_id == task_id`.
   - Task must exist.
   - `task.worker_id == worker_id`.
   - Active lease must exist and belong to the task.
   - Worker workspace paths must resolve inside the lease workspace root.
   - Project-root paths must stay inside the project root.
   - Sensitive names/dirs such as `.env`, `.env.local`, `.env.production`, `.git`, `data`, `logs`, `__pycache__`, `.pytest_cache` must be rejected or skipped.
   - Symlink escape and symlink-to-denied-dir behavior must stay consistent with read/list/write tools.

3. Summary behavior:
   - Return JSON only.
   - Scan worker workspace files up to `max_files` bounded to 1..200.
   - Return safe per-file metadata only: relative path, status (`created`, `modified`, `same`), worker bytes, project bytes, text/binary/oversized flags, and lease/task/worker ids.
   - Do not return raw file content, raw task goal, steps, prompts, env vars, shell output, request strings, or secrets.
   - If a worker file maps to a sensitive project path, skip or return a bounded safe error; do not read sensitive project files.

4. Patch export behavior:
   - Return JSON only.
   - If `path` is provided, export a patch for that one safe file; otherwise export patches for changed safe files up to `max_files`.
   - Compare project-root file content to worker workspace file content.
   - Created files should produce unified diff from empty content.
   - Modified files should produce unified diff against the project-root version.
   - Same files should not appear in exported patch output unless a single requested path is same, in which case return a bounded no-change result.
   - Patch output must be bounded by existing workspace byte limits and total result should stay bounded.
   - Binary/non-UTF8/oversized files return bounded JSON errors or per-file skipped metadata.
   - Do not write to project root or mutate worker/task/lease state.

5. Compatibility:
   - Preserve existing behavior of workspace lease tools, file inspection tools, write tools, sandbox guard tools, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` covering:

- Summary detects created, modified, and same files.
- Patch export for a created file.
- Patch export for a modified file.
- Single-path export and no-change result.
- `max_files` and `context_lines` bounds.
- Relative/absolute path escape rejected.
- Sensitive `.env`, `.env.local`, `.env.production`, `.git`, `logs`, `data`, and cache paths rejected or skipped.
- Symlink escape and symlink-to-denied-dir rejected/skipped.
- Unknown worker, no lease, task mismatch, offline/idle worker rejected.
- Oversized/binary/non-UTF8 project or worker files return bounded JSON errors/skips.
- Outputs do not leak task goal, steps, secret sentinels, raw shell/env/request strings, or unrelated raw file content.
- Tools do not mutate filesystem, task/worker/lease ownership/status, or existing write/read/list/preview behavior.

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
