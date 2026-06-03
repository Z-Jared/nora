# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-099: Scheduler retry decision event metadata v1

## Context

Recent scheduler work now covers closeout planning, guarded run-once/tick/loop, scheduler explainability, read-only retry planning, guarded retry execution, and deterministic eval coverage for retry execution.

The next runtime gap is observability: scheduler decision events need enough bounded metadata to explain retry decisions after the fact, without leaking task content or workspace details.

## Goal

Extend scheduler decision durable event metadata so retry executed/skipped/failed/finalized decisions are auditable and explainable from events, while preserving bounded/no-leak output.

## Requirements

- Inspect how `run_worker_lifecycle_scheduler_tick(..., record_event=True)` and `run_worker_lifecycle_scheduler_loop(..., record_event=True)` currently record `SCHEDULER_DECISION` events.
- Extend event payloads so retry-related decisions are visible in durable events:
  - retry executed
  - retry skipped because task not failed / retry exhausted / active owner / missing idle capacity
  - retry execution failed with bounded reason
  - closeout finalized and dispatch skipped should remain represented at least as well as today.
- Event metadata must be bounded and safe:
  - Include stable safe fields such as `action`, `task_id`, `worker_id` when present, `reason`, `executed`, `skipped`, `failed`, `retry_count`, `max_retries`, and aggregate counts.
  - Do not include task goal, steps, notes, prompts, file contents, raw diffs, reviewer summaries, shell/env/request strings, workspace paths, or secrets.
- Preserve existing API output shape unless a minimal additive field is clearly needed.
- Preserve `record_event=False` semantics: no scheduler decision event should be recorded when disabled.
- Preserve dry-run behavior and existing guarded execution behavior from TASK-097.
- Keep event payload sizes bounded; do not persist raw `results` if it can contain unbounded or unsafe fields. Prefer a sanitized per-action summary list if needed.

## Tests

Add focused unit tests in `tests/test_durable_workers.py`, covering at least:

- Tick with `record_event=True` and retry executed records a `scheduler_decision` event with safe retry action metadata and aggregate counts.
- Tick with retry skipped for missing capacity records safe skip reason metadata.
- Tick/loop with `record_event=False` records no scheduler decision event.
- Loop with retry executed records bounded per-tick/action metadata or equivalent aggregate retry metadata.
- Safety/no-leak: event payload does not contain task goal, steps, failure_reason sentinel, shell/env/request strings, workspace path, or secrets.
- Compatibility: existing scheduler tick/loop/run-once behavior and evals still pass.

Run:

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
python3 evals/run_evals.py
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

## Notes

- TASK-098 eval coverage is already committed on main.
- Keep implementation scoped to scheduler decision event metadata and focused tests.
- If you find existing scheduler event metadata is already sufficient, add tests proving it and explain that in A_DONE.md rather than changing runtime.
