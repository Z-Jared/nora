# Code Review Report

Reviewed: TASK-087 guarded worker lifecycle run-once + TASK-088 lifecycle planner eval coverage
Workers: Claude A (TASK-087), Claude B (TASK-088)
Status: APPROVED after Codex PM fixes

## Findings

### Must Fix

- None remaining.

### Fixed During Review

- `run_worker_lifecycle_once` was registered as `task/write` without explicit confirmation even though `dry_run=False` mutates task, worker, and lease state. PM changed the permission to require confirmation and added test coverage.
- `run_worker_lifecycle_once` could under-report non-finalized finalize attempts because they were neither executed nor skipped. PM added `failed_count` for bounded accounting.
- `eval_lifecycle_planner_no_mutation` used the stale `list_events(limit=...)` API. PM updated it to `max_results=...`.
- The lifecycle planner 100-candidate regression reused earlier ready fixtures, so the assertion did not isolate the intended ordering case. PM moved that regression into a fresh registry state.

## Review Notes

- TASK-087 adds guarded `run_worker_lifecycle_once(limit=5, dry_run=True, release_workspace=True)`.
- Default dry-run does not mutate durable task, worker, lease, project root, worker workspace, shell, or git state.
- Non-dry-run executes only `finalize_ready_workspace_merge` actions and skips wait/dispatch recommendations.
- TASK-088 adds deterministic offline evals for planner ready paths, guard rails, safety/no-leak, no-mutation, missing lease behavior, and compatibility.

## Checks Run

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests
Ran 42 tests in 1.590s
OK

python3 evals/run_evals.py
304 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 604 tests in 16.548s
OK

python3 -m unittest discover -s tests
Ran 1963 tests in 126.243s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Verdict

TASK-087 and TASK-088 APPROVED.

Ready for Codex PM commit and push.
