# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-067: Deterministic eval coverage for worker workspace file inspection.

TASK-066 runtime is approved locally by Codex PM. Start implementation now.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-066 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, or browser sessions.

Planned deterministic offline eval coverage:

1. Valid scoped file inspection:
   - Prepare/claim a worker workspace.
   - Create files under the leased workspace using test setup code.
   - `list_worker_workspace_files` returns bounded relative paths only.
   - `read_worker_workspace_file` reads only inside the active lease.
   - `preview_worker_workspace_write` returns a diff/preview and does not mutate files.

2. Sandbox rejection:
   - Relative traversal escape rejected.
   - Absolute path escape rejected.
   - Empty path error.
   - Unknown worker, no lease, task mismatch, offline worker, and idle worker rejected.
   - Sensitive paths such as `.env` and `.git` rejected.

3. Safety:
   - Outputs do not leak raw task goals, steps, prompts, shell output, env vars, request strings, or secret-like sentinels.
   - Listing output is bounded and relative.
   - Read output is bounded and handles missing/oversized/binary or unsafe files without crashing.

4. Compatibility:
   - File inspection and preview do not mutate task/worker/lease/event state.
   - Error calls do not break existing worker/task registry tools, workspace lease tools, sandbox guard tools, or claim/dispatch.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files and explain why in `agent_tasks/B_DONE.md`.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
