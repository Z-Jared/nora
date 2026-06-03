# Claude B Completion Report - TASK-082

Status: approved by Codex PM

## Summary

Added deterministic offline eval coverage for `finalize_worker_workspace_merge`.

Coverage added:
- Successful finalization: apply, finalize, task completed, worker idle/current_task_id cleared, lease released, safe event metadata.
- Guard rails: no apply, missing lease, stale apply event predating the active lease, invalid `release_workspace`, `release_workspace=False`, repeated finalization, non-running task.
- Safety: no task goal, step, secret, file content, raw exception, shell/env/request leakage.
- Mutation checks: rejection paths do not mutate task, worker, lease, project root, or worker workspace.
- Compatibility after failed and successful finalization.

## Diff

```text
 evals/run_evals.py | 348 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 348 insertions(+)
```

## Verification

```text
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
- Codex PM adjusted one eval path collision after restoring no-changes apply rejection.
