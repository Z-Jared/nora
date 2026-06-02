# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-075: Deterministic eval coverage for worker workspace reviewed merge dry-run.

TASK-074 runtime is approved and visible in the worktree. Start implementation now.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-074 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, browser sessions, project-root merges, patch applies, git writes, process isolation, Docker, UI changes, or model routing.

Planned deterministic offline eval coverage:

1. Ready path:
   - Prepare/claim a worker workspace.
   - Create and modify safe files.
   - Record approved review gate.
   - `dry_run_worker_workspace_merge` returns `ready: true`, no reasons, approved decision, counts, patch counts, patch bytes, worker/task/lease ids.

2. Not-ready review states:
   - No review gate returns `ready: false`, `requires_review: true`, `no_review_gate`.
   - Latest `changes_requested` and `blocked` gates return `ready: false` with `gate_changes_requested` / `gate_blocked`.
   - Approved gate with no changes returns `ready: false`, `no_changes`.

3. Skipped and budget cases:
   - Sensitive/project symlink-to-sensitive-file case is not ready and does not leak the sentinel.
   - Binary or oversized skipped entries are not ready.
   - Multi-file patch budget overflow is not ready with `patch_export_has_skipped` and `patch_budget_exceeded`.

4. Validation and safety:
   - Unknown worker, no lease, task mismatch, offline worker, idle worker, and bad `max_files` are rejected.
   - Output does not leak raw patch text, raw file content, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
   - Error outputs are bounded and do not leak raw exception strings.

5. No-mutation and compatibility:
   - Dry-run does not mutate project root, worker workspace, worker/task state, lease ownership, or review gate.
   - Existing worker/task registry, workspace lease, sandbox guard, read/list/preview/write, change summary/patch export, review gate, claim, and dispatch tools still work after dry-run.

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
