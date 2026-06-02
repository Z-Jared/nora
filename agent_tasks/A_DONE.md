# Claude A Completion Report — TASK-076: Worker Workspace Reviewed Merge Apply v1

Status: approved by Codex PM

## Summary

Added `apply_reviewed_worker_workspace_merge(worker_id, task_id, max_files=50)`, a guarded apply tool that copies approved worker workspace changes into the project root.

Codex PM review fixes:

- Re-check summary skipped entries and patch export skipped/budget state immediately before apply.
- Replaced raw write/rollback exception output with bounded reason labels.
- Added safer rollback failure metadata without raw exception strings.
- Strengthened coverage for patch budget, project symlink-to-sensitive-file, binary/oversized files, error redaction, event safety, and preview/write/claim/dispatch compatibility.

## Diff

```text
 mini_agent/toolkits/registry_builder.py | 214 ++++++++++++
 tests/test_durable_workers.py           | 600 +++++++++++++++++++++++++++++++-
 2 files changed, 814 insertions(+), 1 deletion(-)
```

## Tests

```text
python3 -m unittest tests.test_durable_workers.WorkspaceApplyMergeTests
Ran 31 tests in 0.488s
OK

python3 -m unittest tests.test_durable_workers
Ran 315 tests in 3.914s
OK

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 482 tests in 8.728s
OK

python3 evals/run_evals.py
272 passed, 0 failed

python3 -m unittest discover -s tests
Ran 1841 tests in 117.959s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push performed.
- Apply is strictly gated: it re-runs dry-run at apply time and rejects unless ready.
- No file deletion semantics were added.
- Rollback restores modified files and removes created files after apply failure.
- Successful apply mutates intended project files only; worker workspace, worker/task state, lease ownership, and review gate remain unchanged.
- Deterministic eval coverage for this apply tool is still pending and assigned as TASK-077.
