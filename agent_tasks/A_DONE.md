# Claude A Completion Report - TASK-083

Status: approved by Codex PM

## Summary

Added `finalize_ready_worker_workspace_merges(limit=10, release_workspace=True)`, a guarded batch finalization tool for ready closeout candidates.

Codex PM review fix applied:
- `limit` now counts ready candidates processed, not raw candidates returned by the closeout query. This prevents earlier not-ready candidates from hiding later ready candidates.

## Diff

```text
 mini_agent/toolkits/registry_builder.py |  50 +++++++
 tests/test_durable_workers.py           | 223 ++++++++++++++++++++++++++++++++
 2 files changed, 273 insertions(+)
```

## Tests

```text
python3 -m unittest tests.test_durable_workers.WorkspaceBatchFinalizeTests
Ran 17 tests in 0.307s
OK

python3 evals/run_evals.py
293 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 561 tests in 10.672s
OK

python3 -m unittest discover -s tests
Ran 1920 tests in 119.776s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push performed.
- Batch tool reuses single-task finalize logic.
- It does not touch project root, delete workspace directories, run shell/git, or auto-start workers.
- Repeated batch calls after closeout process zero ready candidates.
