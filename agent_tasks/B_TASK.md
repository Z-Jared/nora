# Claude B Task

Owner: Claude B
Status: waiting

## Goal

Waiting for TASK-093 to land before starting TASK-094.

## Pending Task

TASK-094: Deterministic eval coverage for scheduler blocker explanation v1

## Dependency

Do not start until Codex PM confirms TASK-093 has landed on `main` and `explain_worker_lifecycle_scheduler_state` is available in your worktree.

## Goal

After TASK-093 lands, add deterministic offline eval coverage for the scheduler blocker/explanation tool.

## Expected Coverage

- Empty state/no action needed.
- Ready closeout explanation.
- Not-ready closeout/missing apply/missing lease explanation.
- Pending task + idle worker dispatch availability and guarded block reason.
- Pending tasks without idle workers.
- Idle workers without pending tasks.
- Offline worker reason.
- `worker_id` and `task_id` filters.
- `limit` clamp and bad argument errors.
- Safety/no-leak for task goal, steps, file content, reviewer summary, shell/env/request-like sentinels, workspace paths, and secrets.
- Compatibility with planner, scheduler tick, scheduler loop, run-once, closeout candidate query, worker/task registry, claim, and dispatch tools.

## If Started Too Early

If `explain_worker_lifecycle_scheduler_state` is not available yet, write `agent_tasks/B_DONE.md` with a clear blocker and run:

```text
agent_tasks/notify_codex.sh B
```

Do not guess runtime behavior.

## Notes

- Last completed task: TASK-092 Deterministic eval coverage for scheduler loop v1.
- TASK-092 has been reviewed and approved by CCB reviewer.
- Do not continue TASK-092 unless Codex PM explicitly reassigns follow-up work.
- Do not commit or push.
