# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-069: Deterministic eval coverage for worker workspace write tools.

TASK-068 runtime is approved and visible in the worktree. Start implementation now.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-068 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, or browser sessions.

Planned deterministic offline eval coverage:

1. Valid scoped writes:
   - Prepare/claim a worker workspace.
   - `write_worker_workspace_file` creates/overwrites only inside the lease workspace.
   - `replace_worker_workspace_file` replaces only existing text inside workspace.
   - `apply_worker_workspace_patch` applies a unified diff only inside workspace.
   - After successful writes, worker-scoped read/list/preview still work.

2. Sandbox rejection:
   - Relative traversal escape rejected.
   - Absolute path escape rejected.
   - Empty path and empty `old_text` errors.
   - Unknown worker, no lease, task mismatch, offline worker, and idle worker rejected.
   - Sensitive paths such as `.env`, `.git`, `logs`, and `data` rejected.
   - Symlink escape and symlink-to-denied-dir rejected.

3. Safety:
   - Outputs/events do not leak raw task goals, steps, prompts, shell output, env vars, request strings, raw patch/content, or secret-like sentinels.
   - Oversized content/file and binary/non-UTF8 existing files return bounded JSON errors.
   - Error calls do not mutate filesystem or durable state.

4. Compatibility:
   - Write tools do not mutate task/worker/lease ownership/status.
   - Error and success calls do not break existing worker/task registry tools, workspace lease tools, file inspection tools, sandbox guard tools, claim, or dispatch.

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
