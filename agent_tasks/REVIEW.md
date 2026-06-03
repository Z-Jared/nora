# Code Review Report

Reviewed: TASK-085 worker lifecycle action planner + TASK-086 batch closeout eval coverage
Workers: Claude A (TASK-085), Claude B (TASK-086)
Status: APPROVED after Codex PM fixes

## Findings

### Must Fix

- None remaining.

### Fixed During Review

- `plan_worker_lifecycle_actions` originally depended on the first 100 raw closeout candidates. PM changed it to scan worker/task pairs individually and prioritize ready closeout actions before wait actions.
- PM added regression coverage for an older ready closeout hidden behind 100 newer not-ready workers.
- Batch closeout evals claimed release/idempotency/file-content coverage but were incomplete. PM added explicit assertions for repeated calls, `release_workspace=False`, and real file-content sentinel input.

## Review Notes

- TASK-085 adds read-only `plan_worker_lifecycle_actions(limit=20)`.
- TASK-086 adds deterministic offline eval coverage for `finalize_ready_worker_workspace_merges`.
- Planner does not dispatch, finalize, merge, write workspaces/project root, run shell, or run git.

## Checks Run

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecyclePlannerTests
Ran 18 tests in 2.217s
OK

python3 evals/run_evals.py
298 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 580 tests in 17.440s
OK

python3 -m unittest discover -s tests
Ran 1939 tests in 126.401s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Verdict

TASK-085 and TASK-086 APPROVED.

Ready for Codex PM commit. No push performed yet.
