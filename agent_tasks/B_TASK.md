# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-082: Deterministic eval coverage for worker workspace merge finalization.

TASK-080 runtime is approved and pushed. Add deterministic offline eval coverage for `finalize_worker_workspace_merge` so the closeout behavior is protected at the eval layer, not only unit tests.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-080 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, browser sessions, git writes, project pushes, process isolation, Docker, UI changes, model routing, worker auto-start, or workspace deletion.

Planned deterministic offline eval coverage:

1. Successful finalization:
   - Set up worker/task/workspace.
   - Create safe worker workspace changes.
   - Record approved review gate.
   - Apply reviewed merge.
   - Finalize.
   - Assert task is completed, worker is idle/current_task_id cleared, lease is released by default, and output includes safe status metadata.

2. Guard rails:
   - Reject before successful apply.
   - Reject when active lease is missing.
   - Reject stale apply event whose lease id does not match the active lease.
   - Reject invalid `release_workspace`.
   - `release_workspace=False` completes task/worker but keeps lease.
   - Repeated finalization returns bounded `already_finalized` metadata.

3. Safety / no-leak:
   - Output and events do not leak raw file content, patch text, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
   - Error outputs are bounded and do not include raw exception strings.

4. No unintended mutation:
   - No project-root or worker workspace deletion.
   - No project-root mutation during finalize beyond files already applied by the apply tool.
   - Rejection paths do not mutate task, worker, lease, project root, or worker workspace.

5. Compatibility:
   - Existing apply, audit, dry-run, summary, patch export, review gate, workspace lease, sandbox guard, read/list/preview/write, claim, and dispatch tools still work after failed finalization queries.
   - After successful finalization, audit/task/worker registry tools still work.

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
