# Claude B Task

Owner: Claude B
Status: completed by Codex PM

## Goal

Add eval coverage for durable event log v1 after Claude A completes TASK-007.

## Instructions

Wait for Claude A to implement `DurableEventStore` and the durable event registry tools. Then add deterministic offline eval coverage.

Add eval cases for:

1. Event store basics:
   - Create/list/get durable events
   - Required fields are present
   - Ordering is newest-first or clearly documented and asserted

2. Task lifecycle events:
   - Start task records creation/start event
   - `run_once()` records step/checkpoint event
   - `update_step(done)` records update/checkpoint event
   - `finish()` records completion event

3. Trace linkage:
   - Agent run records trace
   - Durable task gets trace_ref
   - Durable event log records the trace-linked event with task_id and trace_id

4. Failure isolation:
   - Fake event store failure does not break task manager or trace recording

Keep evals deterministic and offline. Do not call live LLM APIs.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_task_runner tests.test_traces
```

## Context

- Current eval count before this task: 85 passing
- Durable task / trace evals are already in `evals/run_evals.py`
- TASK-007 should add the event store API and registry tools
- If Claude A is not done yet, wait; do not reimplement TASK-007

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.
