# Claude A Completion Report - TASK-081

Status: approved by Codex PM

## Summary

Added read-only `list_worker_workspace_merge_closeout_candidates(worker_id="", task_id="", limit=20)` for PM closeout queue discovery.

Codex PM review fixes applied:
- Reverted out-of-scope `WorkspaceLeaseStore` lease id generation change.
- Reverted out-of-scope `apply_reviewed_worker_workspace_merge` no-op apply semantic change.
- Added a safer apply-event matcher: `workspace_merge_apply` must match worker/task/lease id and must not predate the active lease creation time.
- Added tests for stale apply events when a released lease id is reused.

## Diff

```text
 mini_agent/toolkits/registry_builder.py | 244 +++++++++++++++++++++-
 tests/test_durable_workers.py           | 345 ++++++++++++++++++++++++++++++++
 2 files changed, 584 insertions(+), 5 deletions(-)
```

## Tests

```text
python3 -m unittest tests.test_durable_workers.WorkspaceApplyMergeTests tests.test_durable_workers.WorkspaceMergeFinalizeTests tests.test_durable_workers.WorkspaceMergeCloseoutCandidateTests
Ran 76 tests in 1.159s
OK

python3 evals/run_evals.py
288 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 544 tests in 9.977s
OK

python3 -m unittest discover -s tests
Ran 1903 tests in 120.450s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push performed.
- Tool is read-only and does not mutate task, worker, lease, review gate, project root, or worker workspace.
- Completed tasks are not visible through all-workers scan after current_task_id is cleared, but remain visible through task_id filter with `already_finalized`.
