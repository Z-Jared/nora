# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-096: Deterministic eval coverage for scheduler retry planning v1

## Context

TASK-095 has landed on `main` in commit `47a0455`, and TASK-094 has landed in commit `ef54490`.

Current relevant tools:

- `plan_worker_lifecycle_actions(limit=20)`
- `explain_worker_lifecycle_scheduler_state(worker_id="", task_id="", limit=20)`

TASK-095 added read-only retry planning/explanation for failed durable tasks. Scheduler execution does not perform retry yet; this task is eval coverage only.

## Goal

Add deterministic offline eval coverage in `evals/run_evals.py` for retry planning and retry explainability, without changing runtime implementation unless a failing eval exposes a real bug.

## Expected Coverage

Add compact, substantive evals covering:

- Failed task with retries remaining is surfaced as `retry_failed_task` / `retry_available`.
- Failed task with `retry_count >= max_retries` is surfaced as exhausted and not recommended for retry.
- Failed task with active RUNNING or ASSIGNED owner worker is blocked/skipped with `retry_blocked_active_worker`.
- Failed task with no idle capacity is explained as `retry_blocked_missing_capacity`.
- Ready closeout remains higher priority than retry in planner output.
- Existing pending-task dispatch recommendations remain lower priority than retry.
- `task_id` filter does not leak unrelated retry entries.
- `worker_id` filter does not leak unrelated worker/task entries; be explicit about expected behavior for retry entries with empty worker id.
- Safety/no-leak for task goal, steps, failure reason, shell/env/request-like sentinels, workspace paths, and secrets.
- Compatibility after retry explain/planning calls: planner, explain, scheduler tick, scheduler loop, run-once, worker/task registry, claim, and dispatch still work.

## Requirements

- Keep evals deterministic and offline: temporary DB/workspace fixtures only, no live LLM/network, no timing dependency.
- Prefer 6-10 compact eval cases rather than duplicating every unit test.
- Assertions must be concrete: check reason/action labels, ordering, counts, filter exclusions, no mutation, and safety sentinels.
- Do not call `retry_durable_task` inside the planning/explain tools; eval setup may use existing registry APIs to create failed/retried task states.
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

- Last completed B task: TASK-094 Deterministic eval coverage for scheduler blocker explanation v1.
- TASK-097 will handle guarded scheduler retry execution later; do not implement execution in this task.
