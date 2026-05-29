# Claude A Task

Owner: Claude A
Status: assigned

## Goal

Implement durable model-call event logging.

## Instructions

The durable event log now records task lifecycle events and tool-call events. Extend it to cover model-call lifecycle events from `MiniAgent`.

Implement a narrow vertical slice:

1. Record durable events around model calls:
   - model call started
   - model call finished
   - model call error
   - streaming final-answer path if it uses `stream_chat`

2. Event shape:
   - Use existing `DurableEventStore`
   - Add explicit event type constants such as `model_call_started`, `model_call_finished`, and `model_call_error`
   - Payload may include safe metadata: provider/model if available, message count, tool schema count, whether streaming was used, response preview, tool_call_count, latency_ms if easy
   - Do not store raw prompts, full messages, raw API keys, tool schemas, or unbounded model output
   - Reuse existing durable event sanitization/redaction behavior

3. Hook points:
   - `mini_agent/controller.py` paths that call `llm.chat(...)`
   - `_stream_answer(...)` path that calls `llm.stream_chat(...)`
   - `run_autonomous(...)`
   - fallback `llm.complete(...)` path if practical

4. Task linkage and failure isolation:
   - If task_id cannot be resolved safely, record model events without `task_id`
   - Event writes must never break model execution, tool execution, trace recording, streaming, or existing run behavior

5. Tests:
   - Add focused unit coverage for successful chat model event
   - Add coverage for model responses that contain tool calls
   - Add coverage for model error event
   - Add coverage for streaming model event
   - Add failure-isolation coverage with a broken event store

Suggested verification:

```bash
python3 -m unittest tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
```

## Context

- `mini_agent/durable_events.py` contains `DurableEventStore` and existing event type constants
- `mini_agent/controller.py` owns LLM call paths
- `tests/test_durable_events.py` has durable tool-call event patterns to mirror
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 1 calls for model/tool/file/shell/test/review events

Keep scope to model-call events only; do not implement replay, model routing, cost accounting, or provider-specific telemetry.

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, tests run, and known limitations.
