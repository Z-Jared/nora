# Claude A Task

Owner: Claude A
Status: completed by Codex PM

## Goal

Implement durable event log v1.

## Instructions

The durable task store, trace linkage, checkpoint creation, and trace_ref preservation are already committed through `3bde500`. The next step is the first vertical slice of the event log from the durable runtime north star.

Implement a small, queryable durable event log:

1. Add a `DurableEventStore` module:
   - Prefer `mini_agent/durable_events.py`
   - Support SQLite via `NoraDB` plus JSONL fallback, matching `DurableTaskStore` style
   - Event fields should include at minimum: `event_id`, `task_id`, `event_type`, `created_at`, `summary`, `payload`, `trace_id`, `checkpoint_id`, `worker_id`
   - Keep the schema small; do not attempt full replay yet

2. Wire event recording into existing flows:
   - `TaskManager.start()` records task created/started
   - `TaskManager.run_once()` records step selected / checkpoint created
   - `TaskManager.update_step()` records step status updates and checkpoint created when applicable
   - `TaskManager.finish()` records task completed
   - Trace linking records a trace-linked event when `MiniAgent` attaches a trace_id to a durable task

3. Add read-only registry tools:
   - `list_durable_events(task_id="", max_results=50)`
   - `get_durable_event(event_id)`

4. Failure isolation:
   - Event log write failures must not break legacy task flow, trace recording, or durable task shadow sync.

5. Tests:
   - Add focused tests for SQLite and JSONL storage
   - Add tests that task lifecycle/checkpoint/trace-link events are recorded
   - Add tests that event write failures are isolated

Suggested verification:

```bash
python3 -m unittest tests.test_durable_events tests.test_task_runner tests.test_traces
python3 evals/run_evals.py
```

## Context

- North star: `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`, Priority 1 Durable trace schema / event log
- Current trace store is turn-level only: `mini_agent/traces.py`
- Current durable task state is in `mini_agent/durable_tasks.py`
- Current lifecycle hooks are mostly in `mini_agent/task_runner.py` and `mini_agent/controller.py`
- Keep scope narrow: first event log slice, not full replay engine

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, tests run, and known limitations.
