# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-097: Guarded scheduler retry execution v1

## Context

Recent scheduler work now covers closeout planning, guarded run-once/tick/loop, scheduler explainability, and read-only retry planning for failed durable tasks. TASK-096 added deterministic eval coverage for the retry planning/explainability behavior.

The next runtime gap is guarded execution: `dry_run=False` scheduler paths should be able to execute a bounded retry only when the task is already proven safe and retryable.

## Goal

Extend guarded worker lifecycle execution so scheduler run-once/tick/loop can execute safe retry actions for failed durable tasks when `dry_run=False`, without weakening existing closeout, dispatch, safety, or dry-run behavior.

## Requirements

- Update the guarded execution paths:
  - `run_worker_lifecycle_once`
  - `run_worker_lifecycle_scheduler_tick`
  - `run_worker_lifecycle_scheduler_loop`
- Preserve current default safety:
  - `dry_run=True` must remain read-only and must not retry, closeout, dispatch, write files, run shell/git/browser/network, or mutate durable state.
  - `dry_run=False` must remain bounded and may execute only already-supported safe actions.
- Add retry execution only for planner actions with `action == "retry_failed_task"` and `reason == "retry_available"`.
- Use existing durable task retry primitives rather than inventing a second state transition.
- Retry execution must be guarded:
  - Task status is still `failed`.
  - `retry_count < max_retries`.
  - No active ASSIGNED/RUNNING owner worker is still attached to that task.
  - Idle capacity exists if the current planner/explain logic requires it for retry availability.
  - Re-check state at execution time, not only at planning time.
- Preserve action priority:
  - Ready closeout remains ahead of retry.
  - Retry remains ahead of dispatch recommendation.
  - Dispatch is still not executed by the scheduler unless an existing explicit policy already allows it.
- Outputs/events must contain bounded safe metadata only:
  - Include action, reason, task_id, retry_count/max_retries or similar safe counters, and outcome.
  - Do not leak task goal, steps, notes, prompts, raw diffs, file contents, reviewer summaries, shell/env/request strings, workspace paths, or secrets.
- Keep failure behavior bounded:
  - If retry execution fails or state becomes stale, record/report a safe skipped/failed outcome.
  - Do not block other safe closeout actions unless the existing scheduler behavior already does so.
- Do not break planner/explain behavior from TASK-095/TASK-096.

## Tests

Add focused unit tests in `tests/test_durable_workers.py`, covering at least:

- `run_worker_lifecycle_once(dry_run=True)` sees retryable actions but does not mutate failed task state.
- `run_worker_lifecycle_once(dry_run=False)` retries one safe retryable failed task and returns bounded safe outcome metadata.
- `run_worker_lifecycle_scheduler_tick(dry_run=False)` can execute retry safely through the tick wrapper.
- `run_worker_lifecycle_scheduler_loop(dry_run=False)` can execute retry safely through the loop wrapper and respects `max_ticks` / `limit`.
- Exhausted retry tasks are skipped and not mutated.
- Failed tasks with active ASSIGNED/RUNNING owner workers are skipped and not mutated.
- Stale-state guard: if state is no longer retryable at execution time, scheduler reports safe skipped/failed outcome.
- Ordering compatibility: ready closeout remains ahead of retry; retry remains ahead of dispatch.
- Safety/no-leak assertions for goal, steps, file content, reviewer, shell/env/request, workspace path, secrets, and failure_reason.
- Compatibility with planner/explain/tick/loop/run-once existing behavior.

Run:

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests
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

## Notes

- TASK-096 eval coverage is already committed on main.
- Keep implementation scoped to guarded runtime execution and focused unit coverage.
- Do not add eval-only coverage in `evals/run_evals.py` unless it is required to prove a runtime bug fix; Claude B can handle broader eval coverage later.
