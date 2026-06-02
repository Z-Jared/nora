# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-077: Deterministic eval coverage for worker workspace reviewed merge apply.

TASK-076 runtime is approved and visible in the worktree. Start implementation now.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-076 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, browser sessions, git writes, project pushes, process isolation, Docker, UI changes, or model routing.

Planned deterministic offline eval coverage:

1. Approved apply path:
   - Prepare worker workspace with safe created and modified text files.
   - Record approved review gate.
   - `apply_reviewed_worker_workspace_merge` writes intended project files only and returns bounded apply metadata.
   - After apply, dry-run reports `no_changes`.

2. Not-ready rejection:
   - No gate, changes_requested, blocked, and no changes all return `applied: false` with safe reason labels.
   - Patch budget overflow and skipped summary/patch cases are rejected before project writes.

3. Safety boundaries:
   - Sensitive path, worker binary, worker oversized, symlink escape, and project symlink-to-sensitive-file cases are rejected and do not leak sentinels.
   - Output does not leak raw file content, raw patch text, task goal, steps, reviewer summary, shell/env/request strings, or secrets.
   - Error outputs are bounded and do not leak raw exception strings.

4. Validation:
   - Unknown worker, no lease, task mismatch, offline worker, idle worker, and bad `max_files` are rejected.

5. Rollback / no-mutation:
   - Simulated later write failure rolls back earlier created/modified project files.
   - Worker workspace, worker/task state, lease ownership, and review gate remain unchanged.

6. Event and compatibility:
   - Successful apply records safe `workspace_merge` file-edit event metadata only.
   - Existing dry-run, summary, patch export, review gate, workspace lease, sandbox guard, read/list/preview/write, claim, and dispatch tools still work after apply.

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
