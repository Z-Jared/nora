# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-090: Deterministic eval coverage for worker lifecycle run-once

## Goal

Add deterministic offline eval coverage for `run_worker_lifecycle_once(limit=5, dry_run=True, release_workspace=True)`.

## Requirements

Add eval cases to `evals/run_evals.py` covering:

- Dry-run ready closeout returns would-execute metadata and does not mutate task/worker/lease/event store/project root/workspace.
- Non-dry-run finalizes ready closeout and returns expected counts/results.
- Multiple ready closeouts obey `limit`.
- Wait actions are skipped and do not mutate state.
- Dispatch recommendations are skipped and do not dispatch.
- `release_workspace=True` releases the lease; `release_workspace=False` keeps it.
- Bad `limit`, bad `dry_run`, bad `release_workspace`, and limit clamp behavior.
- Failed finalize accounting if the action becomes stale between plan and execute. If simulating this requires a small monkeypatch, keep it local to the eval and deterministic.
- Safety/no-leak for task goal, steps, file content, reviewer summary, shell/env/request-like sentinels, workspace paths, and secrets.
- Compatibility with planner, scheduler tick if present, batch finalize, single-task finalize, closeout candidate query, worker/task registry, claim, and dispatch tools.

## Constraints

- Eval must be deterministic and offline.
- Do not use real LLM calls.
- Prefer adding eval-only helper functions near the existing lifecycle planner evals.
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
