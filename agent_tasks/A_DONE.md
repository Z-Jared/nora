# Claude A Completion Report — TASK-085: Worker Lifecycle Action Planner v1

Status: approved by Codex PM

## Summary

Added `plan_worker_lifecycle_actions(limit=20)`, a read-only planning tool that recommends next worker lifecycle actions for Codex PM without executing anything.

Implementation:
- Queries closeout candidates to identify ready-to-finalize and not-ready worker/task pairs.
- Queries workers and tasks to identify idle workers and pending/unassigned tasks.
- Returns deterministic action labels:
  - `finalize_ready_workspace_merge` for ready closeout candidates.
  - `wait_for_workspace_merge_apply` for running workers without a successful apply.
  - `wait_for_workspace_lease` for workers with invalid/missing leases.
  - `dispatch_pending_task` when idle workers and pending tasks coexist.
- Returns summary counts: `ready_closeouts`, `not_ready_closeouts`, `idle_workers`, `pending_tasks`.
- `limit` bounded 1..100; bad limit returns bounded JSON error.
- Registered with `risk="read"` permission.
- Does not mutate tasks, workers, leases, events, project root, or workspaces.

Codex PM review fix applied:
- Planner now scans worker/task pairs individually instead of relying on the first 100 raw closeout candidates.
- Ready closeout actions are prioritized before wait actions, so an older ready closeout is not hidden by newer not-ready workers.
- Added regression coverage for the 100 raw-candidate boundary.

## Diff

```text
 mini_agent/toolkits/registry_builder.py |  90 +++++++++++
 tests/test_durable_workers.py           | 233 ++++++++++++++++++++++++++
 2 files changed, 323 insertions(+)
```

## Tests

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecyclePlannerTests
Ran 18 tests in 2.217s
OK

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 580 tests in 17.440s
OK

python3 evals/run_evals.py
298 passed, 0 failed

python3 -m unittest discover -s tests
Ran 1939 tests in 126.401s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push performed.
- Purely read-only: no auto-dispatch, no auto-finalize, no mutations.
- Output is safe: no task goals, steps, file contents, paths, or secrets.
