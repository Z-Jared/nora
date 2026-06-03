# Claude B Done

Owner: Claude B
Status: completed
Task: TASK-094 Deterministic eval coverage for scheduler blocker explanation v1

## Summary

Added 13 deterministic offline eval cases for `explain_worker_lifecycle_scheduler_state` in `evals/run_evals.py`:

1. **explain_empty_state** — Empty state returns `no_action_needed`.
2. **explain_ready_closeout** — Ready closeout explanation with concrete reason and next action.
3. **explain_not_ready_closeout** — Not-ready closeout: missing apply or missing lease.
4. **explain_dispatch_available** — Pending task + idle worker: `dispatch_available` with `dispatch_blocked_in_scheduler` detail.
5. **explain_pending_no_idle_workers** — Pending tasks without idle workers: `no_idle_workers` detail.
6. **explain_idle_no_pending** — Idle workers without pending tasks: `no_pending_tasks` reason.
7. **explain_offline_worker** — Offline worker reason via `worker_unavailable` closeout candidate.
8. **explain_worker_filter** — `worker_id` filter returns only matching entries.
9. **explain_task_filter** — `task_id` filter returns only matching entries.
10. **explain_filter_no_leak** — Filtered output does not leak unrelated worker/task data.
11. **explain_limit_clamp_and_bad_args** — Limit clamp and bad argument errors.
12. **explain_safety_no_leak** — Output does not leak goals, steps, file content, reviewer summary, shell/env/request sentinels, workspace paths, or secrets.
13. **explain_compatibility** — Existing tools still work after explain call.

## Runtime Fix

One targeted fix in `mini_agent/toolkits/registry_builder.py`:

- **Filter workers by `task_id`**: When `task_id` filter is set, `workers` output is now filtered to only workers with `current_task_id` matching the requested task. This prevents leaking unrelated worker IDs when filtering by a specific task.

Note: The `worker_unavailable` → `worker_offline` handler and `worker_id` task filter were already present in main (from TASK-095 merge). Only the `task_id` worker filter was missing.

## Diff (vs main)

```text
 evals/run_evals.py                      | 326 ++++++++++++++++++++++++++++++
 mini_agent/toolkits/registry_builder.py |   3 +
```

## Tests

```text
python3 evals/run_evals.py
336 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 688 tests in 11.917s
OK

git diff --check
OK
```

## Notes

- No push was performed by Claude B.
- Runtime change is minimal: 3 lines added to filter workers by task_id.
- TASK-095 retry planning code from main is preserved (not removed).
