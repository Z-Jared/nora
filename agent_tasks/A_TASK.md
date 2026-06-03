# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-089: Worker lifecycle scheduler tick v1

## Goal

Add a guarded scheduler tick tool that promotes the worker lifecycle planner/run-once tools into the first scheduler layer without starting any background process.

Suggested tool name:

`run_worker_lifecycle_scheduler_tick(limit=5, dry_run=True, release_workspace=True, record_event=True)`

## Requirements

- Register the tool in the default registry.
- Permission must be `task/write` with `requires_confirmation=True`, because `dry_run=False` can mutate task/worker/lease state.
- Default must be `dry_run=True`.
- Reuse existing `plan_worker_lifecycle_actions` / `run_worker_lifecycle_once` logic rather than duplicating finalize logic.
- `dry_run=True` must not mutate task/worker/lease/project root/worker workspace.
- `dry_run=False` may execute only ready closeout actions through existing run-once/finalize logic.
- Do not dispatch pending tasks in this task. Report dispatch as skipped / blocked with a clear reason.
- Do not execute wait actions. Report wait states with structured reason labels.
- Do not start loops, background processes, workers, shell commands, git commands, browser actions, network calls, project-root writes, or worker-workspace writes.
- `limit` accepts integers only, defaults to 5, clamps to 1..100, and rejects bool/float/string with bounded error JSON.
- `dry_run`, `release_workspace`, and `record_event` must be booleans.
- Output must be bounded JSON with at least:
  - `scheduler`
  - `tick_id`
  - `dry_run`
  - `record_event`
  - `planned_count`
  - `executed_count`
  - `skipped_count`
  - `failed_count`
  - `blocked_count`
  - `results`
  - `summary`
  - `decision_event_recorded`
- Add a durable scheduler decision event when `record_event=True`.
  - Prefer adding an explicit event type such as `scheduler_decision` to `mini_agent/durable_events.py`.
  - If adding a new event type is too invasive, use existing `task_status_changed` only as a last resort and explain that in `A_DONE.md`.
  - Event payload must contain only safe metadata: counts, action labels, worker/task ids, reason labels, dry_run, release_workspace, and tick id.
- Output and event payload must not include task goals, steps, prompts, file contents, raw diffs, workspace paths, project-root paths, reviewer summaries, shell/env/request strings, or secrets.

## Tests

Add focused unit tests, preferably in `tests/test_durable_workers.py`, covering:

- Default dry-run returns a scheduler tick result and does not mutate task/worker/lease.
- Non-dry-run finalizes a ready closeout through existing closeout path.
- Wait actions are blocked/skipped with reason labels and do not mutate.
- Dispatch recommendations are blocked/skipped and do not dispatch.
- Scheduler decision event is recorded with safe metadata when `record_event=True`.
- `record_event=False` does not record the scheduler event.
- Bad `limit`, bad booleans, and limit clamps.
- Permission requires confirmation.
- Safety/no-leak for goal/steps/file content/reviewer summary/shell/env/request sentinels.
- Compatibility with planner, run-once, batch finalize, candidate query, worker/task registry, claim, and dispatch tools.

Run:

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests
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
