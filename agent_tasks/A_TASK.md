# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-091: Worker lifecycle scheduler loop v1

## Goal

Add a guarded finite scheduler loop on top of `run_worker_lifecycle_scheduler_tick`. This is still not a daemon/background process. It should run a bounded number of scheduler ticks in one tool call.

Suggested tool name:

`run_worker_lifecycle_scheduler_loop(max_ticks=3, limit=5, dry_run=True, release_workspace=True, stop_when_idle=True, record_event=True)`

## Requirements

- Register the tool in the default registry.
- Permission must be `task/write` with `requires_confirmation=True`.
- Default must be `dry_run=True`.
- Reuse existing `run_worker_lifecycle_scheduler_tick` logic. Do not duplicate finalize or planner logic.
- No background loop, daemon, process start, worker start, shell, git, browser, network, project-root writes, or worker-workspace writes.
- `max_ticks` accepts integers only, defaults to 3, clamps to 1..10, and rejects bool/float/string with bounded error JSON.
- `limit` accepts integers only, defaults to 5, clamps to 1..100, and rejects bool/float/string with bounded error JSON.
- `dry_run`, `release_workspace`, `stop_when_idle`, and `record_event` must be booleans.
- Each tick should call the scheduler tick tool/function with the same dry-run/release/event settings.
- If `stop_when_idle=True`, stop early when a tick has no planned actions and no pending/blocked work from summary.
- Output must be bounded JSON with at least:
  - `scheduler`
  - `loop_id`
  - `dry_run`
  - `max_ticks`
  - `ticks_run`
  - `stopped_reason`
  - aggregate `planned_count`, `executed_count`, `skipped_count`, `failed_count`, `blocked_count`
  - `ticks` containing bounded per-tick summaries
  - `summary`
- If `record_event=True`, record a bounded scheduler event for the loop summary, preferably using existing `scheduler_decision`.
- Event payload must contain only safe metadata: counts, tick ids, reason labels, action labels, worker/task ids, dry-run, release flag, and loop id.
- Output and events must not include task goals, steps, prompts, file contents, raw diffs, workspace paths, project-root paths, reviewer summaries, shell/env/request strings, or secrets.

## Tests

Add focused unit tests, preferably in `tests/test_durable_workers.py`, covering:

- Default dry-run loop returns bounded ticks and does not mutate task/worker/lease.
- Non-dry-run loop finalizes ready closeouts through existing tick/run-once path.
- `max_ticks` bounds and clamps.
- `stop_when_idle=True` stops early on empty state.
- `stop_when_idle=False` runs requested bounded tick count.
- Dispatch/wait actions remain blocked/skipped and do not dispatch.
- Loop event is recorded when `record_event=True`; no loop event when false.
- Bad numeric/boolean args return bounded errors.
- Permission requires confirmation.
- Safety/no-leak for goal/steps/file content/reviewer/shell/env/request sentinels.
- Compatibility with scheduler tick, run-once, planner, batch finalize, candidate query, worker/task registry, claim, and dispatch tools.

Run:

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
git diff --check
```

## Boundaries

- Do not edit `agent_tasks/B_TASK.md` or `agent_tasks/B_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/A_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh A
```
