# Claude B Completion Report - TASK-084

Status: approved by Codex PM

## Summary

Added deterministic offline eval coverage for `list_worker_workspace_merge_closeout_candidates`.

Coverage added:
- Ready path with correct worker/task/lease/status/apply event metadata.
- Guard rails: no apply, already finalized, offline/idle worker, task not running, no lease, stale apply from old lease, filters, limit bounds, bad limit.
- Safety/no-leak for goal, secret, step, file content, and bounded error output.
- No mutation of task, worker, lease, project root, or worker workspace.
- Compatibility with finalize, audit, worker/task registry, claim, and dispatch tools.

## Diff

```text
 evals/run_evals.py | 363 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 363 insertions(+)
```

## Verification

```text
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
- No runtime changes were needed for TASK-084.
