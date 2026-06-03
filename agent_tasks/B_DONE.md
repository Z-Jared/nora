# Claude B Done

Owner: Claude B
Status: completed
Task: TASK-092 Deterministic eval coverage for scheduler loop v1

## Summary

Added 11 deterministic offline eval cases for `run_worker_lifecycle_scheduler_loop` in `evals/run_evals.py`:

1. **loop_dry_run_no_mutation** — Default dry-run loop does not mutate task/worker/lease/project root/workspace.
2. **loop_max_ticks_and_limit** — Bounded `max_ticks` (0→1, 999→10) and `limit` (0→1, 999→100) clamping.
3. **loop_stop_when_idle_true** — `stop_when_idle=True` stops early on empty state.
4. **loop_stop_when_idle_false** — `stop_when_idle=False` runs the requested bounded tick count.
5. **loop_non_dry_run_closeout** — Non-dry-run finalizes ready closeouts, does not dispatch pending tasks. Verifies pending task stays `pending`/unassigned, idle worker stays untasked, and dispatch action has `skipped=True, reason=dispatch_blocked_in_tick` in tick event payload.
6. **loop_dispatch_wait_blocked** — Dispatch blocked with `reason=dispatch_blocked_in_tick`, wait skipped with `reason=wait_action`, verified via tick event payload `actions` array.
7. **loop_record_event_true** — Loop scheduler event is recorded with safe bounded metadata.
8. **loop_record_event_false** — `record_event=False` avoids loop event recording.
9. **loop_bad_params** — Bad `max_ticks`, `limit`, `dry_run`, `release_workspace`, `stop_when_idle`, `record_event` return bounded errors; valid clamps verified.
10. **loop_safety_no_leak** — Output does not leak goal, steps, file content, reviewer summary, shell/env/request sentinels, workspace paths, or secrets (dry-run and non-dry-run).
11. **loop_compatibility** — Existing tools (scheduler tick, run-once, planner, batch finalize, single-task finalize, closeout candidate query, worker/task registry, claim, dispatch) still work after loop call.

## PM Review Fix

Fixed two weak evals identified by PM:

- **eval_loop_non_dry_run_closeout**: Rewrote to verify that when ready closeout + idle worker + pending task coexist, `dry_run=False` finalizes closeout but pending task remains `pending`/unassigned, idle worker stays untasked, and dispatch action has `skipped=True, reason=dispatch_blocked_in_tick` in tick event payload.
- **eval_loop_dispatch_wait_blocked**: Rewrote to assert concrete reason labels from tick event payload: dispatch action has `reason=dispatch_blocked_in_tick`, wait action has `reason=wait_action`, both `skipped=True`.

## Diff

```text
 evals/run_evals.py | 295 +++++++++++++++++++++++++++++++-
```

## Tests

```text
python3 evals/run_evals.py
323 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 651 tests in 11.759s
OK

git diff --check
OK
```

## Notes

- No push was performed by Claude B.
- No runtime implementation changes required.
