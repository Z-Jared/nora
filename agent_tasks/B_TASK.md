# Claude B Task

Owner: Claude B
Status: completed

## Task

TASK-100: Deterministic eval coverage for scheduler retry decision event metadata v1

## Context

TASK-099 extended scheduler decision durable event metadata for retry decisions:

- Tick `SCHEDULER_DECISION` events now include bounded retry action metadata and aggregate retry counts.
- Loop `SCHEDULER_DECISION` events now include aggregate retry counts and bounded per-tick retry counts.
- `record_event=False` should still record no scheduler decision events.
- Event payloads must not leak task goal, steps, failure_reason, shell/env/request strings, workspace paths, file contents, raw results, or secrets.

Unit coverage exists in `tests/test_durable_workers.py`. The remaining gap is deterministic offline eval coverage in `evals/run_evals.py`.

## Goal

Add deterministic eval cases proving scheduler retry decision event metadata is auditable, bounded, no-leak, and compatible.

## Requirements

- Add focused eval coverage in `evals/run_evals.py` for TASK-099 behavior.
- Prefer small helper functions and isolated temp DB/workspace fixtures consistent with existing scheduler retry evals.
- Cover at least:
  1. Tick retry executed event metadata:
     - `run_worker_lifecycle_scheduler_tick(dry_run=False, record_event=True)` records a `scheduler_decision` event.
     - Event payload includes `retry_executed >= 1`, `retry_skipped`, `retry_failed`.
     - `actions[]` contains a `retry_failed_task` entry with safe fields such as `executed=True`, `task_id`, `retry_count`, `max_retries`.
  2. Tick retry skipped metadata:
     - Missing idle capacity or equivalent guarded skip records a safe retry skipped reason such as `retry_blocked_missing_capacity`.
     - No task mutation happens when skipped.
  3. Loop retry metadata:
     - `run_worker_lifecycle_scheduler_loop(dry_run=False, max_ticks=1, record_event=True)` records a loop `scheduler_decision` event.
     - Loop payload includes aggregate `retry_executed`, `retry_skipped`, `retry_failed`.
     - Loop payload includes bounded `ticks[]` per-tick retry counts.
     - It does not persist raw `results`.
  4. `record_event=False`:
     - Tick and loop with `record_event=False` produce no scheduler decision events.
  5. Safety/no-leak:
     - Event payloads and eval-observed output do not contain task goal, steps, failure_reason sentinel, shell/env/request strings, workspace path, raw results, or secret-like sentinels.
  6. Compatibility:
     - Existing evals still pass and scheduler tick/loop/run-once/planner/explain remain callable after the new metadata checks.

## Tests

Run:

```text
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests tests.test_durable_workers.SchedulerRetryEventMetadataTests
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
git diff --check
```

## Boundaries

- Prefer eval-only changes in `evals/run_evals.py`.
- Do not modify runtime unless an eval exposes a real TASK-099 bug; if that happens, keep the runtime fix minimal and explain it in `B_DONE.md`.
- Do not edit `agent_tasks/A_TASK.md` or `agent_tasks/A_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/B_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh B
```

## Notes

- TASK-099 is committed on `main`.
- Keep eval assertions concrete; avoid tests that only assert event existence.
- Keep outputs bounded and safe; do not store or assert raw task content, file contents, raw patch/diff, or unbounded result objects.
