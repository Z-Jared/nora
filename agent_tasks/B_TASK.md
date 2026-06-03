# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-098: Deterministic eval coverage for guarded scheduler retry execution v1

## Context

TASK-097 has landed on `main` in commit `df58f35`.

Current relevant tools:

- `plan_worker_lifecycle_actions(limit=20)`
- `explain_worker_lifecycle_scheduler_state(worker_id="", task_id="", limit=20)`
- `run_worker_lifecycle_once(limit=5, dry_run=True, release_workspace=True)`
- `run_worker_lifecycle_scheduler_tick(limit=5, dry_run=True, release_workspace=True, record_event=True)`
- `run_worker_lifecycle_scheduler_loop(max_ticks=3, limit=5, dry_run=True, release_workspace=True, stop_when_idle=True, record_event=True)`

TASK-097 added guarded scheduler retry execution. When `dry_run=False`, scheduler run-once/tick/loop can execute planner-produced `retry_failed_task` actions only when execution-time guards pass.

## Goal

Add deterministic offline eval coverage in `evals/run_evals.py` for guarded scheduler retry execution, without changing runtime implementation unless a failing eval exposes a real bug.

## Expected Coverage

Add compact, substantive evals covering:

- `run_worker_lifecycle_once(dry_run=True)` returns retry would-execute metadata and does not mutate failed task state.
- `run_worker_lifecycle_once(dry_run=False)` retries exactly a safe retryable failed task, moving it back to pending and incrementing `retry_count`.
- Scheduler tick and scheduler loop wrappers execute the retry path when `dry_run=False`.
- No idle capacity skips retry with `retry_blocked_missing_capacity` and does not mutate the task.
- Active owner worker blocks retry for both `ASSIGNED` and `RUNNING` states.
- Stale execution-time guard is covered: planner can see a retry action, but execution observes a changed task state and skips/fails safely without retrying.
- Ready closeout still happens before retry; dispatch remains skipped/not executed.
- Safety/no-leak for task goal, steps, failure reason, shell/env/request-like sentinels, workspace paths, and secrets.
- Compatibility after retry execution calls: planner, explain, scheduler tick, scheduler loop, run-once, worker/task registry, claim, and dispatch still work.

## Requirements

- Keep evals deterministic and offline: temporary DB/workspace fixtures only, no live LLM/network, no timing dependency.
- Prefer 6-10 compact eval cases rather than duplicating every unit test.
- Assertions must be concrete: check result action labels, skip reasons, mutation/no-mutation, retry_count/status, ordering, and safety sentinels.
- It is acceptable for eval setup to use registry APIs to create failed/retried task states. The scheduler execution under test may call `retry_durable_task` only through `run_worker_lifecycle_once` / tick / loop with `dry_run=False`.
- Do not change runtime unless an eval exposes a real bug; if runtime changes are needed, keep them minimal and document them in `B_DONE.md`.

## Required Checks

```text
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
git diff --check
```

## Boundaries

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

- Last completed B task: TASK-096 Deterministic eval coverage for scheduler retry planning v1.
- Keep this eval-focused. Runtime changes should only happen if an eval reveals a real TASK-097 bug.
