# Claude A Completion Report — TASK-074: Worker Workspace Reviewed Merge Dry-Run v1

Status: approved by Codex PM

## Summary

Added read-only `dry_run_worker_workspace_merge(worker_id, task_id, max_files=50)` to preflight whether a worker workspace is ready for a future reviewed merge flow.

Codex PM review fixes:

- Fixed dry-run patch budget detection to honor `patch_bytes` and skipped patch reasons returned by `export_worker_workspace_patch`.
- Strengthened skipped-entry coverage for patch budget and project symlink-to-sensitive-file cases.
- Strengthened compatibility coverage for preview/write plus claim/dispatch after dry-run.
- Fixed a review-time indentation issue before verification.

## Diff

```text
 mini_agent/toolkits/registry_builder.py |  96 ++++++++
 tests/test_durable_workers.py           | 407 ++++++++++++++++++++++++++++++++
 2 files changed, 503 insertions(+)
```

## Tests

```text
python3 -m unittest tests.test_durable_workers
Ran 284 tests in 3.362s
OK

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 451 tests in 8.670s
OK

python3 evals/run_evals.py
265 passed, 0 failed

python3 -m unittest discover -s tests
Ran 1810 tests in 117.193s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push performed.
- Dry-run is purely read-only: it does not write project root, worker workspace, task, worker, or lease state.
- `ready` remains conservative: no approval gate, non-approved gate, no changes, skipped summary entries, skipped patch entries, or patch budget overflow all return `ready: false`.
- Known limitation: deterministic eval coverage for this dry-run tool is still pending and assigned as TASK-075.
