# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-092: Deterministic eval coverage for scheduler loop v1

## Goal

Add deterministic offline eval coverage for scheduler loop v1 after Claude A lands `run_worker_lifecycle_scheduler_loop`.

## Requirements

Add eval cases to `evals/run_evals.py` covering:

- Default dry-run loop does not mutate task/worker/lease/project root/workspace.
- Bounded `max_ticks` and `limit` behavior.
- `stop_when_idle=True` stops early on empty state.
- `stop_when_idle=False` runs the requested bounded tick count.
- Non-dry-run closeout-only execution finalizes ready closeouts and does not dispatch pending tasks.
- Dispatch recommendations and wait actions are returned as blocked/skipped with reason labels.
- Loop scheduler event is recorded with safe bounded metadata when `record_event=True`.
- `record_event=False` avoids loop event recording.
- Bad `max_ticks`, `limit`, `dry_run`, `release_workspace`, `stop_when_idle`, and `record_event` values return bounded errors.
- Safety/no-leak for task goal, steps, file content, reviewer summary, shell/env/request-like sentinels, workspace paths, and secrets.
- Compatibility with scheduler tick, run-once, planner, batch finalize, single-task finalize, closeout candidate query, worker/task registry, claim, and dispatch tools.

## Constraints

- Eval must be deterministic and offline.
- Do not use real LLM calls.
- If `run_worker_lifecycle_scheduler_loop` is not available yet in your worktree, write `B_DONE.md` with a clear blocker and notify Codex PM instead of guessing runtime behavior.
- Do not change runtime implementation unless an eval exposes a clear bug; if so, stop and report it in `B_DONE.md`.
- Avoid broad refactors.

## Tests

Run:

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
