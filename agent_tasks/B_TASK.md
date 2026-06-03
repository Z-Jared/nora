# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-079: Deterministic eval coverage for worker workspace merge apply audit/history.

TASK-078 runtime is approved and visible in the worktree. Start implementation now.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-078 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, browser sessions, git writes, project pushes, process isolation, Docker, UI changes, or model routing.

Planned deterministic offline eval coverage:

1. Empty and result basics:
   - `list_worker_workspace_merge_applies` returns empty list before apply.
   - Successful apply creates an audit row with event_id, created_at, worker_id, task_id, lease_id, applied_count, created_count, modified_count, and safe paths.

2. Filters and limits:
   - worker_id and task_id filters work.
   - limit is bounded to 1..100.
   - bad limit returns bounded JSON error.
   - limit applies after operation filtering so unrelated workspace_merge events do not hide valid apply events.

3. Malformed payload safety:
   - Malformed counts become 0.
   - Non-list paths become [].
   - Sensitive, redacted, denied, traversal, and absolute paths are omitted.
   - Malformed/sensitive ids do not leak secrets.

4. No-leak / read-only:
   - Output does not leak raw file content, patch text, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
   - Audit query does not mutate project root, worker workspace, worker/task state, lease ownership, or review gate.

5. Compatibility:
   - Existing apply, dry-run, summary, patch export, review gate, workspace lease, sandbox guard, read/list/preview/write, claim, and dispatch tools still work after audit query.

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
