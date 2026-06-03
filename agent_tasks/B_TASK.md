# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-094: Deterministic eval coverage for scheduler blocker explanation v1

## Context

TASK-093 has landed on `main` in commit `1b092a1`. The tool `explain_worker_lifecycle_scheduler_state(worker_id="", task_id="", limit=20)` is available in the default registry.

## Goal

Add deterministic offline eval coverage for the scheduler blocker/explanation tool in `evals/run_evals.py`.

## Expected Coverage

- Empty state/no action needed.
- Ready closeout explanation.
- Not-ready closeout/missing apply/missing lease explanation.
- Pending task + idle worker dispatch availability and guarded block reason.
- Pending tasks without idle workers.
- Idle workers without pending tasks.
- Offline worker reason.
- `worker_id` and `task_id` filters.
- Regression coverage for filtered output:
  - `task_id=dtask_1` must not leak `dtask_2` or unrelated worker reasons/actions.
  - `worker_id=w1` must not leak `w2` or unrelated task reasons/actions.
- `limit` clamp and bad argument errors.
- Safety/no-leak for task goal, steps, file content, reviewer summary, shell/env/request-like sentinels, workspace paths, and secrets.
- Compatibility with planner, scheduler tick, scheduler loop, run-once, closeout candidate query, worker/task registry, claim, and dispatch tools.

## Requirements

- Keep evals deterministic and offline: use temporary DB/workspace fixtures, no live LLM/network, no timing dependency.
- Do not change runtime implementation unless a failing eval exposes a real TASK-093 bug; if that happens, stop and report the bug in `agent_tasks/B_DONE.md` instead of broad runtime edits.
- Eval assertions must be substantive: assert concrete reason labels, filter exclusions, read-only/no mutation, and safety sentinels.
- Do not duplicate every unit test mechanically; prefer compact eval scenarios that catch integration regressions and compatibility issues.

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

- Last completed task: TASK-092 Deterministic eval coverage for scheduler loop v1.
- TASK-092 has been reviewed and approved by CCB reviewer.
- Do not commit or push.
