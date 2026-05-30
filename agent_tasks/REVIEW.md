# CCB Code Review Report

Reviewed: TASK-015 Durable shell-command event logging
Worker: Claude A; Codex PM tightened raw command handling
Status: **APPROVED**

---

## Review Scope

### 1. Lifecycle Correctness

**Verdict: ✅ CORRECT**

All shell-command lifecycle paths properly instrumented in `mini_agent/shell.py`:

**`run()` method lifecycle:**

- ✅ **BLOCKED** (disallowed command): line 101-102
  - `_parse_allowed_command()` returns None → `SHELL_COMMAND_BLOCKED` with `error="disallowed_command"`
  - No STARTED event emitted

- ✅ **BLOCKED** (cancelled): line 107-108
  - User denies confirmation → `SHELL_COMMAND_BLOCKED` with `error="cancelled"`
  - No STARTED event emitted

- ✅ **STARTED**: line 110
  - After allowlist + confirmation pass, before `subprocess.run()`
  - Records parsed argv (safe, not raw command)

- ✅ **FINISHED**: line 137-144
  - On subprocess completion (including nonzero exit codes)
  - Records exit_code, stdout_bytes, stderr_bytes

- ✅ **ERROR** (timeout): line 124-131
  - `subprocess.TimeoutExpired` → `SHELL_COMMAND_ERROR` with `error="timeout"`
  - Records stdout_bytes, stderr_bytes from timed-out process

- ✅ **ERROR** (OSError): line 133-135
  - `OSError` during subprocess execution → `SHELL_COMMAND_ERROR` with `error="os_error"`

### 2. Safe Durable Payloads

**Verdict: ✅ SAFE**

Payload contains only safe metadata (line 70-79 in shell.py):

```python
payload = {
    "executable": executable,      # first element of parsed argv only
    "argv_count": len(parts),      # integer count
    "status": status,              # "started"/"finished"/"blocked"/"cancelled"/"timeout"/"error"
    "exit_code": exit_code,        # integer (None for blocked/started)
    "timeout": status == "timeout", # boolean
    "stdout_bytes": stdout_bytes,  # integer byte count
    "stderr_bytes": stderr_bytes,  # integer byte count
    "error": error,                # generic label only
}
```

**Generic error labels (not raw exceptions):**
- ✅ `"disallowed_command"` — command not in allowlist
- ✅ `"cancelled"` — user confirmation denied
- ✅ `"timeout"` — subprocess.TimeoutExpired
- ✅ `"os_error"` — OSError during execution

**Summary field (line 68):**
- ✅ `f"{event_type}: {executable or 'unknown'}"` — only event type and executable name

**Explicitly excluded from payload/summary/serialized records:**
- ❌ Raw full command string
- ❌ Raw arguments (individual argv elements)
- ❌ stdout/stderr content
- ❌ Raw exception text (e.g., "NORA_SHELL_OS_ERROR_SECRET_2048")
- ❌ Reason text (user-provided justification)
- ❌ Secrets/sentinel values
- ❌ Unbounded output

**Verified by sentinel tests:**
- `test_no_raw_command_in_payload` — "NORA_SHELL_ARG_SECRET_8842" ABSENT from serialized events
- `test_no_raw_output_in_serialized_events` — "NORA_SHELL_STDOUT_SECRET_4921" ABSENT from serialized events
- `test_no_raw_timeout_output_in_serialized_events` — "NORA_SHELL_TIMEOUT_OUTPUT_SECRET_1173" ABSENT from serialized events
- `test_no_raw_os_error_in_serialized_events` — "NORA_SHELL_OS_ERROR_SECRET_2048" ABSENT from serialized events
- `test_malformed_blocked_command_records_without_raw_command` — "NORA_SHELL_BLOCKED_SECRET_7365" ABSENT from serialized events

### 3. Failure Isolation

**Verdict: ✅ RELIABLE**

`_record_shell_event()` method (shell.py:49-82):

```python
def _record_shell_event(self, ...) -> None:
    if not self.event_store:
        return
    try:
        # ... build payload and record ...
        self.event_store.record(...)
    except Exception:
        pass
```

**Verified by tests:**
- ✅ `test_failure_isolation_broken_event_store` — BrokenEventStore raises RuntimeError, `run()` still succeeds, returns correct result
- ✅ `test_no_event_store_does_not_break_shell` — event_store=None, `run()` still succeeds

**Additional isolation:**
- ✅ All event recording wrapped in try/except with `pass`
- ✅ No event_store = immediate return (no-op)
- ✅ Event failures cannot break shell command execution
- ✅ Event failures cannot alter user-visible return strings

### 4. Compatibility

**Verdict: ✅ COMPATIBLE**

**Direct ShellRunner use:**
- ✅ `ShellRunner(root, event_store=event_store)` — works for direct instantiation
- ✅ `ShellRunner(root, event_store=None)` — works without event store
- ✅ `ShellRunner(root, event_store=BrokenEventStore())` — works with broken store

**Default registry wiring (registry_builder.py:132):**
```python
shell_runner.event_store = durable_event_store
```

**Verified by test:**
- ✅ `test_default_registry_wires_shell_events` — registry.call("run_shell_command") emits events, verifies STARTED and FINISHED lifecycle

**No unintended changes:**
- ✅ No test-run instrumentation added
- ✅ No unrelated behavior changes
- ✅ Existing shell command behavior preserved (disallowed commands still blocked, confirmations still required)

### 5. Test Quality — Substantive and Deterministic

**Verdict: ✅ COMPREHENSIVE**

`ShellCommandDurableEventTests` class (15 test methods):

1. **`test_successful_command_records_started_and_finished`** — verifies lifecycle, executable="pwd", exit_code=0, status="finished", stdout_bytes > 0
2. **`test_disallowed_command_records_blocked`** — verifies blocked-only lifecycle, no STARTED, no FINISHED, error="disallowed_command"
3. **`test_cancelled_command_records_blocked`** — verifies blocked-only lifecycle, no STARTED, error="cancelled"
4. **`test_timeout_records_error_with_allowed_command`** — verifies STARTED→ERROR lifecycle, error="timeout", status="timeout", timeout=True, stdout_bytes > 0
5. **`test_nonzero_exit_still_records_finished`** — verifies FINISHED emitted for nonzero exit_code, exit_code != 0
6. **`test_no_raw_command_in_payload`** — verifies sentinel "NORA_SHELL_ARG_SECRET_8842" ABSENT, executable="python3" PRESENT
7. **`test_no_raw_output_in_serialized_events`** — verifies sentinel "NORA_SHELL_STDOUT_SECRET_4921" ABSENT, stdout_bytes > 0 PRESENT
8. **`test_no_raw_timeout_output_in_serialized_events`** — verifies sentinel "NORA_SHELL_TIMEOUT_OUTPUT_SECRET_1173" ABSENT, error="timeout" PRESENT
9. **`test_no_raw_os_error_in_serialized_events`** — verifies sentinel "NORA_SHELL_OS_ERROR_SECRET_2048" ABSENT, error="os_error" PRESENT
10. **`test_malformed_blocked_command_records_without_raw_command`** — verifies sentinel "NORA_SHELL_BLOCKED_SECRET_7365" ABSENT, executable="", argv_count=0
11. **`test_failure_isolation_broken_event_store`** — verifies run() succeeds despite BrokenEventStore
12. **`test_no_event_store_does_not_break_shell`** — verifies run() succeeds with event_store=None
13. **`test_shell_event_no_task_id`** — verifies all events have task_id=None
14. **`test_payload_has_executable_and_argv_count`** — verifies executable="ls", argv_count=2
15. **`test_default_registry_wires_shell_events`** — verifies registry integration emits STARTED and FINISHED

**Assertion quality:**
- ✅ No empty assertions (all verify specific payload fields, lifecycle sequences, or sentinel values)
- ✅ Strong negative assertions (sentinel values ABSENT from serialized events)
- ✅ Positive assertions verify exact values (not just presence)
- ✅ Deterministic: no timing dependencies, no network calls, no external state

---

## Checks Run

```text
python3 -m unittest tests.test_durable_events tests.test_mini_agent
Ran 203 tests — OK

python3 evals/run_evals.py
103 passed, 0 failed

python3 -m unittest discover -s tests
Ran 1183 tests — OK

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

- ✅ **Safety**: No raw data exposure (command strings, args, output, exceptions, secrets)
- ✅ **Lifecycle**: All shell-command paths correctly instrumented (blocked, started, finished, error)
- ✅ **Isolation**: Event failures cannot break shell execution
- ✅ **Compatibility**: Both direct use and registry wiring work, no unintended changes
- ✅ **Backward Compat**: No event_store = no-op behavior preserved
- ✅ **Test Coverage**: 15 comprehensive tests with strong assertions

---

## Verdict

**APPROVED**

TASK-015 is ready for commit and merge. Implementation meets all safety, correctness, and coverage requirements. No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
