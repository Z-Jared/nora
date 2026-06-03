# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-095: Retryable failed-task planning for worker lifecycle scheduler v1

## Context

Recent scheduler work now covers closeout planning, guarded run-once/tick/loop, and scheduler explainability. The next gap from the runtime north-star is retry/backoff awareness for failed durable tasks.

## Goal

Extend the read-only worker lifecycle planning/explainability tools so Codex PM can see which failed durable tasks are safely retryable before enabling scheduler-side retry execution.

## Requirements

- Update `plan_worker_lifecycle_actions` and `explain_worker_lifecycle_scheduler_state`.
- Keep this task read-only:
  - Do not call `retry_durable_task`.
  - Do not mutate durable task, worker, lease, event, filesystem, shell, git, browser, network, or project-root state.
- Detect retryable failed tasks using existing durable-task metadata:
  - Task status is failed.
  - `retry_count < max_retries`.
  - No active/running owner worker still attached.
  - Skip terminal/non-retryable cases cleanly.
- Add stable action/reason labels for retry planning/explanation. Suggested labels:
  - `retry_available`
  - `retry_exhausted`
  - `retry_blocked_active_worker`
  - `retry_blocked_missing_capacity`
  - `retry_not_needed`
  You may adjust labels if the existing naming scheme suggests a better fit, but keep them stable and explicit.
- Planner expectations:
  - Include retry recommendations in `planned_actions` using bounded safe metadata only.
  - Keep existing ready-closeout priority ahead of retry recommendations when both exist.
  - Preserve deterministic ordering.
- Explainability expectations:
  - Surface retryable failed tasks in `blocked_reasons` / `next_actions` with clear explanation of whether retry is available now or blocked.
  - Do not leak task goal, steps, notes, prompts, raw diffs, file contents, reviewer summaries, shell/env/request strings, workspace paths, or secrets.
- Compatibility:
  - Do not break current closeout planning, dispatch recommendations, or filter semantics from TASK-093.

## Tests

Add focused unit tests in `tests/test_durable_workers.py`, covering at least:

- Failed task with retries remaining is surfaced as retryable.
- Failed task with exhausted retries is not recommended for retry.
- Failed task with active/running owner worker is blocked/skipped with stable reason.
- Planner still prioritizes ready closeout ahead of retry recommendation.
- Explain output with `worker_id` / `task_id` filters does not leak unrelated retry entries.
- Safety/no-leak assertions for goal, steps, file content, reviewer, shell/env/request, workspace path, secrets.
- Read-only / no-mutation verification.
- Compatibility with existing planner/explain/tick/loop/run-once tools.

Run:

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecyclePlannerTests tests.test_durable_workers.WorkerLifecycleExplainStateTests
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

- TASK-094 is already in progress for Claude B and edits `evals/run_evals.py`; avoid overlap with eval-only work.
- Keep implementation scoped to planner/explain read-only behavior; scheduler execution changes can come later.
