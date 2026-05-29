# Claude A Task

Owner: Claude A
Status: completed

## Goal

Implement durable tool-call event logging.

## Instructions

The durable event log v1 is committed in `b18beba` and current main is `fe20206`. Your task is to extend the event log from task lifecycle events to tool-call events.

Implement a narrow vertical slice:

1. Record durable events from `MiniAgent` tool execution:
   - Successful tool call
   - Tool call error
   - Blocked/cancelled permissioned tool call
   - Tool result budget/compaction behavior if already represented by current run records

2. Event shape:
   - Use existing `DurableEventStore`
   - Event types can be simple strings such as `tool_call_started`, `tool_call_finished`, `tool_call_blocked`, `tool_call_error`
   - Payload should include tool name, status, result preview, and safe/truncated arguments preview
   - Do not store secrets or full unbounded tool results

3. Task linkage:
   - If there is an active durable task, include its task_id when practical.
   - If task_id cannot be resolved safely, record the event without task_id rather than failing.

4. Failure isolation:
   - Event writes must never break tool execution, trace recording, or existing run behavior.

5. Tests:
   - Add/extend focused tests for successful tool events
   - Add/extend focused tests for tool errors
   - Add/extend focused tests for blocked/cancelled tool calls
   - Add failure-isolation test with a broken event store

Suggested verification:

```bash
python3 -m unittest tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
```

## Context

- `mini_agent/durable_events.py` contains `DurableEventStore`
- `mini_agent/controller.py` owns tool execution and run events
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 1 calls for model/tool/file/shell/test/review events
- Keep scope to tool-call events only; do not implement replay or model-call events yet

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, tests run, and known limitations.
