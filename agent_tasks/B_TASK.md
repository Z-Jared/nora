# Claude B Task

Owner: Claude B
Status: assigned

## Goal

Add eval coverage for durable tool-call event logging after Claude A completes TASK-009.

## Instructions

Wait for Claude A to implement TASK-009. Then add deterministic offline eval coverage for tool-call events.

Add eval cases for:

1. Successful tool call event:
   - Run a local/tool-backed prompt or direct agent flow that invokes a tool
   - Verify durable event log records tool name, status, and safe result preview

2. Tool error event:
   - Invoke a failing tool path
   - Verify durable event log records an error/blocked status without crashing

3. Permission cancellation event:
   - Use an unconfirmed permissioned tool path
   - Verify durable event log records blocked/cancelled status

4. Failure isolation:
   - Broken event store should not change existing tool execution behavior

Keep evals offline and deterministic. Do not call live LLM APIs.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_mini_agent
```

## Context

- Current eval count before this task: 89 passing
- `evals/run_evals.py` already has durable event lifecycle evals
- If TASK-009 is not complete, wait; do not reimplement it

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.
