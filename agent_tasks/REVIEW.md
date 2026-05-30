# CCB Code Review Report

Reviewed: TASK-017 Durable test-run event logging for `Diagnostics.run_tests`
Worker: Claude A; Codex PM tightened payload safety
Status: **APPROVED**

---

## Review Scope

### 1. Lifecycle Correctness

**Verdict: ✅ CORRECT**

All test-run lifecycle paths properly instrumented in `mini_agent/diagnostics.py`:

**`run_tests()` method lifecycle:**

- ✅ **BLOCKED** (disallowed command): line 76
  - Command != `ALLOWED_TEST_COMMAND` → `TEST_RUN_BLOCKED` with `error="disallowed_command"`
  - No STARTED event emitted

- ✅ **STARTED**: line 80
  - After command validation, before `subprocess.run()`
  - Records `max_output_chars`

- ✅ **FINISHED**: line 113-119
  - On subprocess completion (including nonzero exit codes)
  - Records exit_code, stdout_bytes, stderr_bytes, max_output_chars

- ✅ **ERROR** (timeout): lines 93-101
  - `subprocess.TimeoutExpired` → `TEST_RUN_ERROR` with `error="timeout"`, `timeout=True`
  - Records stdout_bytes, stderr_bytes from timed-out process

- ✅ **ERROR** (OSError): lines 103-109
  - `OSError` during subprocess execution → `TEST_RUN_ERROR` with `error="os_error"`

### 2. Safe Durable Payloads

**Verdict: ✅ SAFE**

Payload contains only bounded metadata (lines 36-44 in diagnostics.py):

```python
payload = {
    "command_kind": "unittest_discover",  # fixed string
    "status": status,                     # "started"/"finished"/"blocked"/"timeout"/"error"
    "exit_code": exit_code,               # integer (None for blocked/started)
    "timeout": timeout,                   # boolean
    "stdout_bytes": stdout_bytes,         # integer byte count
    "stderr_bytes": stderr_bytes,         # integer byte count
    "error": error,                       # generic label only
    "max_output_chars": max_output_chars, # integer (optional)
}
```

**Generic error labels (not raw exceptions):**
- ✅ `"disallowed_command"` — command not in allowlist
- ✅ `"timeout"` — subprocess.TimeoutExpired
- ✅ `"os_error"` — OSError during execution

**Summary field (line 52):**
- ✅ `f"{event_type}: unittest_discover"` — only event type and fixed command kind

**Explicitly excluded from payload/summary/serialized records:**
- ❌ Raw stdout/stderr content
- ❌ Traceback/failure bodies
- ❌ Full command/args strings
- ❌ Reason text (user-provided justification)
- ❌ Raw exception text (e.g., "NORA_TEST_OS_ERROR_SECRET_9910")
- ❌ Sentinel secrets
- ❌ Unbounded output

**Verified by sentinel tests (lines 1303-1310):**
- `COMMAND_SENTINEL = "NORA_TEST_COMMAND_SECRET_2319"` — raw command arg
- `OUTPUT_SENTINEL = "NORA_TEST_OUTPUT_SECRET_8221"` — raw stdout content
- `ERROR_SENTINEL = "NORA_TEST_OS_ERROR_SECRET_9910"` — raw OSError text
- `REASON_SENTINEL = "NORA_TEST_REASON_SECRET_4437"` — raw reason text

**Forbidden payload keys (10 keys, line 1307-1310):**
```python
FORBIDDEN_PAYLOAD_KEYS = {
    "command", "args", "argv",       # raw command/args
    "stdout", "stderr", "output",    # raw output
    "result",                        # raw result
    "reason",                        # user-provided reason
    "exception", "traceback",        # raw error details
}
```

**`_assert_events_safe()` method (lines 1342-1348):**
- ✅ Serializes all test-run events to JSON
- ✅ Checks all forbidden values are ABSENT from serialized data
- ✅ Checks all 10 forbidden payload keys are ABSENT from event payloads

### 3. Failure Isolation

**Verdict: ✅ RELIABLE**

`_record_test_run_event()` method (diagnostics.py:23-57):

```python
def _record_test_run_event(self, ...) -> None:
    if not self.event_store:
        return
    # ... build payload ...
    try:
        self.event_store.record(...)
    except Exception:
        pass
```

**Verified by tests:**
- ✅ `test_failure_isolation_broken_event_store` (line 1431) — BrokenEventStore raises RuntimeError, `run_tests()` still succeeds
- ✅ `test_no_event_store_does_not_break_tests` (line 1440) — event_store=None, `run_tests()` still succeeds

**Additional isolation:**
- ✅ All event recording wrapped in try/except with `pass`
- ✅ No event_store = immediate return (no-op)
- ✅ Event failures cannot break test execution
- ✅ Event failures cannot alter user-visible return strings

### 4. Compatibility

**Verdict: ✅ COMPATIBLE**

**Direct Diagnostics use:**
- ✅ `Diagnostics(root, event_store=event_store)` — works for direct instantiation
- ✅ `Diagnostics(root, event_store=None)` — works without event store
- ✅ `Diagnostics(root, event_store=BrokenEventStore())` — works with broken store

**Default registry wiring (registry_builder.py:133):**
```python
diagnostics.event_store = durable_event_store
```

**Verified by test:**
- ✅ `test_default_registry_wires_test_run_events` (line 1465) — registry.call("run_project_tests") emits events, verifies STARTED and FINISHED lifecycle, `registry.diagnostics.event_store` is not None

**No unintended changes:**
- ✅ No changes to shell behavior (ShellRunner)
- ✅ No changes to eval behavior (run_evals.py)
- ✅ No changes to retry/repair-loop behavior
- ✅ Existing run-test output semantics preserved (lines 101, 121-128)

### 5. Test Quality — Deterministic and Substantive

**Verdict: ✅ COMPREHENSIVE**

`TestRunDurableEventTests` class (10 test methods):

1. **`test_successful_test_run_records_started_and_finished`** (line 1350)
   - ✅ Verifies lifecycle: [STARTED, FINISHED]
   - ✅ Checks command_kind="unittest_discover", max_output_chars=12000
   - ✅ Checks status="finished", exit_code=0, stdout_bytes + stderr_bytes > 0
   - ✅ Verifies reason sentinel ABSENT

2. **`test_disallowed_command_records_blocked`** (line 1370)
   - ✅ Verifies blocked-only lifecycle: [BLOCKED], no STARTED, no FINISHED
   - ✅ Checks error="disallowed_command"
   - ✅ Verifies command sentinel ABSENT

3. **`test_failing_tests_still_records_finished`** (line 1384)
   - ✅ Verifies FINISHED emitted for nonzero exit_code
   - ✅ Checks exit_code != 0
   - ✅ Verifies output sentinel ABSENT from events (present in user-visible result)

4. **`test_timeout_records_error`** (line 1400)
   - ✅ Verifies STARTED → ERROR lifecycle
   - ✅ Checks error="timeout", timeout=True
   - ✅ Verifies output sentinel ABSENT

5. **`test_os_error_records_generic_error_without_raw_exception`** (line 1418)
   - ✅ Verifies ERROR lifecycle
   - ✅ Checks error="os_error"
   - ✅ Verifies error sentinel ABSENT from both user-visible result and events

6. **`test_failure_isolation_broken_event_store`** (line 1431)
   - ✅ Verifies run_tests() succeeds despite BrokenEventStore

7. **`test_no_event_store_does_not_break_tests`** (line 1440)
   - ✅ Verifies run_tests() succeeds with event_store=None

8. **`test_test_run_event_no_task_id`** (line 1445)
   - ✅ Verifies all events have task_id=None

9. **`test_payload_has_command_kind`** (line 1452)
   - ✅ Verifies command_kind="unittest_discover", max_output_chars=900

10. **`test_default_registry_wires_test_run_events`** (line 1465)
    - ✅ Verifies registry integration emits STARTED and FINISHED
    - ✅ Verifies `registry.diagnostics.event_store` is not None

**Assertion quality:**
- ✅ No empty assertions (all verify specific payload fields, lifecycle sequences, or sentinel values)
- ✅ Strong negative assertions (sentinel values ABSENT from serialized events)
- ✅ Positive assertions verify exact values (not just presence)
- ✅ Deterministic: no timing dependencies, no network calls, no external state

---

## Checks Run

```text
python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent
Ran 227 tests — OK

python3 evals/run_evals.py
108 passed, 0 failed

python3 -m unittest discover -s tests
Ran 1193 tests — OK

git diff --check
OK
```

---

## Findings

### Must Fix

**None** — implementation is production-ready.

### Suggestions

**None** — code quality is high, no technical debt introduced.

### Risk Assessment

- ✅ **Safety**: No raw data exposure (stdout, stderr, tracebacks, commands, reasons, exceptions, secrets)
- ✅ **Lifecycle**: All test-run paths correctly instrumented (blocked, started, finished, timeout, OSError)
- ✅ **Isolation**: Event failures cannot break test execution
- ✅ **Compatibility**: Both direct use and registry wiring work, no unintended changes to shell/eval/retry/repair-loop
- ✅ **Backward Compat**: No event_store = no-op behavior preserved
- ✅ **Test Coverage**: 10 comprehensive tests with 4 sentinels + 10 forbidden keys

---

## Verdict

**APPROVED**

TASK-017 is ready for commit and merge. Implementation meets all safety, correctness, and coverage requirements. No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
