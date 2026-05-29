# Claude B Task

Owner: Claude B
Status: assigned

## Goal

Add eval coverage for durable model-call event logging after Claude A completes TASK-011.

## Instructions

Wait for Claude A to implement TASK-011. Then add deterministic offline eval coverage for model-call events.

Add eval cases for:

1. Successful model call event:
   - Use a fake `llm.chat(...)`
   - Verify durable event log records started/finished events and safe response preview

2. Model call with tool-call response:
   - Use a fake LLM that returns a tool call, then a final answer
   - Verify durable model events include tool_call_count metadata without storing raw prompts

3. Model call error event:
   - Use a fake LLM that raises `LLMError`
   - Verify durable event log records model error without crashing existing blocked/error behavior

4. Streaming model event:
   - Use fake `stream_chat(...)`
   - Verify stream path records model event metadata and preserves streamed output

5. Failure isolation:
   - Broken event store should not change existing `run()` or `run_events()` behavior

Keep evals offline and deterministic. Do not call live LLM APIs.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_mini_agent
```

## Context

- Current eval count before this task: 93 passing
- `evals/run_evals.py` already has durable event lifecycle and tool-call event evals
- If TASK-011 is not complete, wait; do not reimplement it

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.
