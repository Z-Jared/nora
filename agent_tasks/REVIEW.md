# Code Review Report

Reviewed: TASK-089 worker lifecycle scheduler tick + TASK-090 run-once eval coverage
Workers: Claude A/B partial diffs; Codex PM completed after provider failure
Status: APPROVED after Codex PM fixes

## Findings

### Must Fix

- None remaining.

### Fixed During Review

- Scheduler tick initially duplicated run-once/finalize execution logic. PM changed it to call existing `_run_worker_lifecycle_once_json` and only wrap results with scheduler-specific blocked counts and decision-event metadata.
- Scheduler decision event initially contained only action labels. PM added bounded per-action metadata with safe action label, worker/task ids, reason label, skipped flag, would-execute flag, and finalized flag.
- Run-once dry-run eval initially expected zero new events, but the tool correctly emits approval events because it is confirmation-gated as `task/write`. PM narrowed the assertion to forbid execution/mutation events.
- Multiple-ready eval setup reused the same `f.txt` path, causing later workers to have no successful merge apply. PM changed the lifecycle eval helper to write worker-specific file paths.
- Release-workspace eval used a contaminated registry state. PM added explicit lease assertions and made the ready helper produce valid unique applies.

## Review Notes

- `run_worker_lifecycle_scheduler_tick` is a single tick only. It does not start a background loop, process, worker, shell command, git command, browser action, or network call.
- Default dry-run remains safe and does not finalize tasks.
- Non-dry-run can only execute ready closeout through existing run-once behavior.
- Dispatch recommendations are blocked in this task, not executed.
- Wait actions are skipped with reason labels.
- Outputs and scheduler event payloads are bounded metadata and do not include task goals, steps, file contents, raw diffs, workspace paths, project-root paths, reviewer summaries, shell/env/request strings, or secrets.

## Checks Run

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests
Ran 61 tests in 2.331s
OK

python3 -m unittest tests.test_durable_workers
Ran 456 tests in 23.635s
OK

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 623 tests in 31.747s
OK

python3 evals/run_evals.py
312 passed, 0 failed

python3 -m unittest discover -s tests
Ran 1982 tests in 134.827s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Verdict

TASK-089 and TASK-090 APPROVED.

Ready for Codex PM commit and push.
