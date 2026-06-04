# Claude B Done

Owner: Claude B
Status: completed

## Task

TASK-100: Deterministic eval coverage for scheduler retry decision event metadata v1

## Summary

Added 6 deterministic offline eval cases in `evals/run_evals.py` covering TASK-099 scheduler retry decision event metadata:

1. **tick_retry_executed_event_metadata**: Tick with retry executed records safe retry action metadata in scheduler_decision event. Verifies aggregate counts (`retry_executed >= 1`, `retry_skipped`, `retry_failed`) and per-action fields (`executed=True`, `task_id`, `retry_count=1`, `max_retries=3`).

2. **tick_retry_skipped_event_metadata**: Tick with retry skipped for missing capacity records safe skip reason. Verifies `retry_skipped >= 1` in payload and per-action `reason="retry_blocked_missing_capacity"`. Confirms no task mutation.

3. **loop_retry_event_metadata**: Loop with retry executed records aggregate and per-tick retry metadata. Verifies aggregate counts and per-tick counts in `ticks[]`. Confirms raw `results` not persisted in event payload.

4. **retry_event_record_false**: Tick and loop with `record_event=False` produce no scheduler decision events.

5. **retry_event_safety_no_leak**: Event payloads do not leak task goal, steps, failure_reason, shell/env/request, workspace paths, or secrets. Uses sentinels and verifies none appear in serialized event payloads.

6. **retry_event_compatibility**: Scheduler tick/loop/run-once/planner/explain remain callable after retry event metadata checks.

## Changes

- `evals/run_evals.py`: Added 6 eval functions + registered in cases list. No runtime changes needed.

## Tests

```
python3 evals/run_evals.py: 364 passed, 0 failed
python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests tests.test_durable_workers.SchedulerRetryEventMetadataTests: 58 tests, OK
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent: 737 tests, OK
git diff --check: clean
```

## Notes

- TASK-099 runtime implementation already handles retry event metadata correctly; this task only adds eval coverage.
- No runtime bugs found; no runtime changes made.
