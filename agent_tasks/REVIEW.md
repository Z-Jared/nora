# CCB Code Review Report

Reviewed: TASK-011 Durable model-call event logging + TASK-012 Eval coverage for model-call events
Worker: Claude A (TASK-011 runtime), Claude B (TASK-012 evals), PM-curated into main worktree
Status: **APPROVED**

---

## Review Scope

### 1. Model-call Event Logging Coverage in `controller.py`

**Verdict: ✅ COMPLETE**

All LLM call paths are properly instrumented:

- ✅ `llm.chat()` via `_call_model()` — used in `_run_with_llm_tools_events()`, `_run_with_llm_tools()` (dead code, consistent), `run_autonomous()`
- ✅ `llm.stream_chat()` via `_stream_answer()` — used in `_run_with_llm_tools_events()` streaming path
- ✅ `llm.complete()` via `_call_model_complete()` — used in `_run_events_inner()` fallback path
- ✅ Autonomous path via `run_autonomous()` — uses `_call_model()` directly
- ✅ All paths emit `MODEL_CALL_STARTED` before call and `MODEL_CALL_FINISHED`/`MODEL_CALL_ERROR` after

### 2. Event Write Failure Isolation

**Verdict: ✅ SAFE**

All event recording is wrapped in try/except in `_record_model_event()`:

```python
def _record_model_event(self, ...) -> None:
    if not self.event_store:
        return
    try:
        # ... record event ...
    except Exception:
        pass
```

- ✅ No event write failure can break model execution
- ✅ No event write failure can break streaming
- ✅ No event write failure can break run_events generator
- ✅ Existing error handling (LLMError, Exception) preserved
- ✅ Backward compatibility maintained (no event_store = no-op)

### 3. Event Payload Safety (No Raw Data)

**Verdict: ✅ SAFE**

Payload contains only safe metadata:

```python
payload = {
    "status": status,                    # "started"/"ok"/"error"
    "streaming": streaming,              # boolean
    "provider_model": provider_model,    # "provider/model" string
    "message_count": msg_count,          # integer count
    "tool_schema_count": tool_count,     # integer count
    "tool_call_count": tool_call_count,  # integer count
    "response_preview": truncated,       # max 120 chars
    "latency_ms": round(ms, 1),         # float
    "error": truncated_error,            # max 200 chars
}
```

**Explicitly excluded:**
- ❌ Raw prompts/messages (only counts stored)
- ❌ Full tool schemas (only count stored)
- ❌ Raw model output (truncated to 120 chars)
- ❌ API keys/tokens/credentials
- ❌ Unbounded response text

**Additionally protected by DurableEventStore:**
- ✅ `_sanitize_string()` applies sensitive text redaction
- ✅ `_is_sensitive_key()` redacts password/token/secret keys
- ✅ String length limits enforced (_PAYLOAD_STRING_LIMIT=1000)

### 4. Eval Coverage Strength (TASK-012)

**Verdict: ✅ STRONG**

5 new eval cases in `evals/run_evals.py`:

1. **`eval_model_call_event_success`** — Uses sentinel prompt `RAW_PROMPT_SHOULD_NOT_BE_STORED_73F1`
   - ✅ Asserts sentinel reaches FakeLLM (proves eval is live)
   - ✅ Asserts sentinel absent from serialized event data
   - ✅ Verifies forbidden payload keys: `messages`, `tools`, `tool_schema`, `tool_schemas`, `functions`, `parameters`
   - ✅ Checks all safe metadata fields present

2. **`eval_model_call_event_with_tool_calls`** — Uses sentinel prompt + tool result
   - ✅ Asserts sentinel prompt reaches model
   - ✅ Asserts sentinel tool result reaches follow-up call
   - ✅ Verifies tool_call_count >= 1
   - ✅ Asserts model events have task_id=None (no spurious binding)

3. **`eval_model_call_event_error`** — Uses FailingLLM
   - ✅ Verifies MODEL_CALL_STARTED emitted
   - ✅ Verifies MODEL_CALL_ERROR emitted (not FINISHED)
   - ✅ Checks error payload contains failure text
   - ✅ Verifies severity="warning"
   - ✅ Ensures agent.run() returns error message (no crash)

4. **`eval_model_call_event_streaming`** — Uses FakeStreamingLLM
   - ✅ Verifies streaming=True in payload
   - ✅ Checks response_preview contains streamed content
   - ✅ Verifies latency_ms present
   - ✅ Validates both started/finished events for streaming

5. **`eval_model_call_event_failure_isolation`** — Uses BrokenEventStore
   - ✅ Tests chat path survives event store failure
   - ✅ Tests run_events stream survives event store failure
   - ✅ Tests streaming path survives event store failure
   - ✅ All paths return correct results

**Shared assertion helper `_assert_model_events_do_not_store_raw_context()`:**
- ✅ Checks all MODEL_CALL_* events in event list
- ✅ Forbids sentinel values in serialized event data
- ✅ Forbids raw context keys (messages, tools, tool_schema, etc.)

### 5. Unit Test Coverage in `test_durable_events.py`

**Verdict: ✅ COMPLETE**

`ModelCallDurableEventTests` class with 7 tests:

1. **`test_successful_chat_records_started_and_finished`** — verifies basic event lifecycle
2. **`test_tool_call_model_event_records_tool_call_count`** — verifies tool call metadata
3. **`test_model_error_records_error_event`** — verifies error handling
4. **`test_streaming_model_event_records_started_and_finished`** — verifies streaming events
5. **`test_model_event_failure_does_not_break_execution`** — verifies broken store isolation
6. **`test_no_event_store_does_not_break_model_calls`** — verifies backward compat
7. **`test_autonomous_model_call_records_events`** — verifies autonomous path

### 6. Status File Consistency

**Verdict: ✅ CONSISTENT**

- `BACKLOG.md`: TASK-011 ✅ completed, TASK-012 review candidate
- `A_DONE.md`: TASK-011 completion report with all required sections
- `B_DONE.md`: TASK-012 completion report with all required sections
- No stale/conflicting state detected

---

## Checks Run

```text
python3 evals/run_evals.py
98 passed, 0 failed

python3 -m unittest tests.test_durable_events tests.test_mini_agent
Ran 175 tests in 0.914s
OK

python3 -m unittest discover -s tests
Ran 1155 tests
OK

git diff --check
passed
```

---

## Findings

### Must Fix

**None** — implementation is production-ready.

### Suggestions

**None** — code quality is high, no technical debt introduced.

### Risk Assessment

- ✅ **Safety**: No raw data exposure (prompts, messages, schemas, keys, unbounded output)
- ✅ **Isolation**: Event failures cannot break model execution
- ✅ **Compatibility**: Backward compatible (no event_store = no-op)
- ✅ **Performance**: Event recording overhead minimal (count + truncation)
- ✅ **Maintainability**: Clean separation between runtime events and evals

---

## Verdict

**APPROVED**

TASK-011 and TASK-012 are ready for commit and merge. Implementation meets all safety, correctness, and coverage requirements. No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
