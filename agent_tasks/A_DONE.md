# Claude A Completion Report

Owner: Claude A
Task: Implement durable model-call event logging
Status: DONE

## Summary

Extended the durable event log to cover model-call lifecycle events from `MiniAgent`. Added three new event types (`model_call_started`, `model_call_finished`, `model_call_error`) and instrumented all LLM call paths in the controller.

## Changes

### `mini_agent/durable_events.py`
- Added `MODEL_CALL_STARTED`, `MODEL_CALL_FINISHED`, `MODEL_CALL_ERROR` constants
- Added them to `VALID_EVENT_TYPES`

### `mini_agent/controller.py`
- Added `import time` for latency tracking
- Added `_record_model_event()` helper — records model-call events with safe metadata (status, streaming flag, message count, tool schema count, tool call count, response preview, latency_ms, provider/model label, error)
- Added `_provider_model_label()` — extracts provider/model from LLM client attributes
- Added `_call_model()` — wraps `self.llm.chat()` with event logging
- Added `_call_model_complete()` — wraps `self.llm.complete()` with event logging
- Instrumented `_run_with_llm_tools_events()` — uses `_call_model()` instead of raw `self.llm.chat()`
- Instrumented `_stream_answer()` — emits started/finished/error events around `self.llm.stream_chat()`
- Instrumented `run_autonomous()` — uses `_call_model()` instead of raw `self.llm.chat()`
- Instrumented `_run_events_inner()` fallback — uses `_call_model_complete()` for `llm.complete()` path
- Instrumented `_run_with_llm_tools()` (dead code, but consistent) — uses `_call_model()`

### `tests/test_durable_events.py`
- Added `ModelCallDurableEventTests` class with 7 tests:
  - `test_successful_chat_records_started_and_finished`
  - `test_tool_call_model_event_records_tool_call_count`
  - `test_model_error_records_error_event`
  - `test_streaming_model_event_records_started_and_finished`
  - `test_model_event_failure_does_not_break_execution`
  - `test_no_event_store_does_not_break_model_calls`
  - `test_autonomous_model_call_records_events`

## Tests Run

```text
python3 -m unittest tests.test_durable_events  → 50 passed
python3 -m unittest tests.test_mini_agent       → 125 passed
python3 evals/run_evals.py                      → 93 passed, 0 failed
```

## Design Notes

- Event payloads contain only safe metadata: provider/model, message count, tool schema count, tool call count, response preview (truncated), latency_ms, error (truncated)
- No raw prompts, full messages, API keys, tool schemas, or unbounded model output stored
- Existing sanitization/redaction from `DurableEventStore._sanitize_value()` applies
- All event writes wrapped in try/except — failures never break model execution
- `task_id` always `None` on model events (no safe task resolution from model calls alone)

## Known Limitations

- `task_id` not resolved for model events (by design)
- Provider/model label relies on LLM client exposing `provider`, `model`, or `model_name` attributes
- `_run_with_llm_tools()` is dead code but instrumented for consistency

## Notes

- No push performed by Claude A.
- No commit performed by Claude A.
