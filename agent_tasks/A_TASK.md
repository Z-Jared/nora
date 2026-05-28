# Claude A Task

Owner: Claude A
Status: assigned

## Goal

Continue durable task integration — wire DurableTaskStore into the default agent build and add CLI commands for task inspection.

## Instructions

The durable task shadow write is implemented and committed (`dbdb7c2`). Now integrate it into the runtime:

1. Wire `DurableTaskStore` into `build_agent()` in `mini_agent/app.py`:
   - Create `DurableTaskStore(db=db)` and pass it to `TaskManager(durable_store=..., enable_durable_shadow=True)`
   - This makes all CLI/HTTP runs persist tasks automatically

2. Add CLI commands for task inspection:
   - `/tasks [n]` — list recent durable tasks
   - `/task <task_id>` — show a specific task with steps and status

3. Add a registry tool:
   - `list_durable_tasks(max_results=20)` — read-only task listing

4. Update README if user-visible commands are added.

5. Add focused tests for the wiring and new tools/commands.

## Context

- `mini_agent/durable_tasks.py` has `DurableTaskStore` with `upsert_task()`, `get_task()`, `list_tasks()`
- `mini_agent/task_runner.py` has `TaskManager` with `durable_store` and `enable_durable_shadow` params
- Current gap: `build_agent()` does not pass a DurableTaskStore, so normal runs don't persist tasks
- Current gap: no user-facing way to list or inspect durable tasks

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, tests run, and known limitations.
