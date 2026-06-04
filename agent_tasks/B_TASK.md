# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-108: Deterministic eval coverage for runtime policy hook summary v1

## Context

TASK-107 added the read-only `summarize_runtime_policy_hook_evaluations(...)` registry tool for aggregating safe bounded `policy_hook_evaluation` durable event metadata. It supports `hook`, `decision`, `category`, `risk`, `task_id`, `worker_id`, `session_id`, and `limit` filters.

The next step is deterministic offline eval coverage for this summary tool.

## Goal

Add deterministic eval coverage in `evals/run_evals.py` for `summarize_runtime_policy_hook_evaluations(...)`.

## Requirements

Add focused offline eval cases that verify:

- Summary counts for allow/confirm/block decisions, hooks, categories, risks, confirmation count, blocked count, policy versions, and recent event IDs.
- `hook`, `decision`, `category`, `risk`, `task_id`, `worker_id`, and `session_id` filters work.
- Recent/limit behavior is deterministic and bounded.
- Invalid/unsafe filters return empty bounded output or safe errors without returning all events.
- Raw reason/action/linkage sentinels, shell commands, env/request strings, workspace paths, and secrets do not leak.
- Summary is read-only and does not create events or mutate durable tasks/workers.
- Compatibility: existing `evaluate_runtime_policy_hook`, `record_runtime_policy_hook_evaluation`, `list_runtime_policy_hook_evaluations`, `summarize_runtime_policy_hook_evaluations`, `list_tool_permissions`, durable event store, and existing evals still work.

Keep the evals deterministic and offline: use temporary directories/local `NoraDB`, no network, no model calls, no shared state.

## Tests

Run:

```text
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
git diff --check
```

## Boundaries

- Do not change runtime behavior unless an eval exposes a real TASK-107 bug; if needed, keep the fix minimal and explain it in `B_DONE.md`.
- Do not edit `agent_tasks/A_TASK.md` or `agent_tasks/A_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/B_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh B
```
