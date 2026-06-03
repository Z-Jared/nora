# Code Review Report

Reviewed: TASK-083 guarded batch closeout + TASK-084 candidate query eval coverage
Workers: Claude A (TASK-083), Claude B (TASK-084)
Status: APPROVED after Codex PM fix

## Findings

### Must Fix

- None remaining.

### Fixed During Review

- Batch finalize originally passed `limit` directly into the candidate query, so not-ready candidates could consume the limit and hide later ready candidates.
- PM changed batch finalize to query up to 100 candidates, then process up to `limit` ready candidates.
- PM added a regression test for not-ready candidates preceding ready candidates.
- Follow-up PM review found that ready candidates older than 100 newer not-ready candidates were still hidden.
- PM changed batch finalize to scan worker/task pairs individually and added a regression test for the 100 raw-candidate boundary.

## Review Notes

- TASK-083 adds `finalize_ready_worker_workspace_merges(limit=10, release_workspace=True)`.
- TASK-084 adds deterministic eval coverage for `list_worker_workspace_merge_closeout_candidates`.
- Batch finalization reuses the single-task finalization path and does not write project root, delete workspaces, run shell/git, or start workers.

## Checks Run

```text
python3 -m unittest tests.test_durable_workers.WorkspaceBatchFinalizeTests
Ran 18 tests in 0.987s
OK

python3 evals/run_evals.py
293 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 562 tests in 11.807s
OK

python3 -m unittest discover -s tests
Ran 1921 tests in 122.559s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Verdict

TASK-083 and TASK-084 APPROVED.

Ready for Codex PM commit. No push performed yet.
