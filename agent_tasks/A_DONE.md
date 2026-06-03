# Claude A — Completion Report

Owner: Claude A
Task: TASK-091 — Worker lifecycle scheduler loop v1
Status: **DONE**

## Summary

Added `run_worker_lifecycle_scheduler_loop` tool on top of the existing `run_worker_lifecycle_scheduler_tick`. The loop runs a bounded number of scheduler ticks in one tool call, with optional early-stop when idle.

## Changes

### `mini_agent/toolkits/registry_builder.py` (+163 lines)

- Added `_scheduler_loop_counter` mutable counter.
- Added `_run_worker_lifecycle_scheduler_loop_json` function:
  - Validates and clamps `max_ticks` (int, 1..10, default 3), `limit` (int, 1..100, default 5), and boolean params (`dry_run`, `release_workspace`, `stop_when_idle`, `record_event`).
  - Rejects bool/float/string for numeric args with bounded error JSON.
  - Generates `loop_id = f"loop_{counter}"`.
  - Iterates up to `max_ticks` times, calling `_run_worker_lifecycle_scheduler_tick_json` each iteration with the same settings.
  - If `stop_when_idle=True`, stops early when a tick has `planned_count == 0` and no pending/blocked work in summary.
  - Aggregates `planned_count`, `executed_count`, `skipped_count`, `failed_count`, `blocked_count` across ticks.
  - Returns bounded JSON: `scheduler`, `loop_id`, `dry_run`, `max_ticks`, `ticks_run`, `stopped_reason`, aggregate counts, `ticks` array, `summary` object, `loop_event_recorded`.
  - If `record_event=True`, records a `SCHEDULER_DECISION` event with `summary="scheduler loop"` and safe metadata only.
- Registered `run_worker_lifecycle_scheduler_loop` tool with `task/write` permission, `requires_confirmation=True`.

### `tests/test_durable_workers.py` (+223 lines)

Added `WorkerLifecycleSchedulerLoopTests` class with 28 tests covering:
- Default dry-run loop returns bounded ticks, no mutation
- Non-dry-run loop finalizes ready closeouts
- `max_ticks` bounds and clamps (0→1, 99→10)
- `max_ticks` bad types (bool/float/string) return errors
- `limit` bad types return errors
- `dry_run`, `release_workspace`, `stop_when_idle`, `record_event` bad types return errors
- `stop_when_idle=True` stops early on empty state
- `stop_when_idle=False` runs all requested ticks
- Dispatch/wait actions remain blocked/skipped
- Loop event recorded when `record_event=True`; none when false
- Permission requires confirmation
- Safety/no-leak for goal, steps, file content, event payload
- Required output fields present
- Compatibility with scheduler tick, run-once, planner

## Verification

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests
→ 61 tests OK

python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests
→ 28 tests OK

python3 -m unittest tests.test_durable_workers
→ 484 tests OK

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
→ 651 tests OK

git diff --check
→ clean
```

## Diff

```text
 mini_agent/toolkits/registry_builder.py | 163 +++++++++++++++++++++++
 tests/test_durable_workers.py           | 223 ++++++++++++++++++++++++++++++++
 2 files changed, 386 insertions(+)
```

## Boundaries Respected

- ✅ Only edited `mini_agent/toolkits/registry_builder.py` and `tests/test_durable_workers.py`
- ✅ Did not edit `agent_tasks/B_TASK.md` or `B_DONE.md`
- ✅ Did not edit `CODEX_TERMINAL_HANDOFF.md` or `designs/`
- ✅ Did not commit or push
- ✅ No background/daemon/shell/network/project-root writes
- ✅ Output/events contain no goal, steps, file content, paths, shell/env/secrets
