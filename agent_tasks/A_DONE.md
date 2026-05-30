# Claude A Completion Report — TASK-015: Durable Shell-Command Event Logging

Status: ready for Codex review

## Summary

Extended the durable event log to cover shell-command lifecycle events from `ShellRunner.run`. Every shell execution now emits `SHELL_COMMAND_STARTED` → `SHELL_COMMAND_FINISHED` or `SHELL_COMMAND_ERROR`/`SHELL_COMMAND_BLOCKED` events with safe metadata. All event writes are failure-isolated. Codex PM tightened the candidate so raw command text is not reparsed for event payloads and blocked malformed commands cannot leak raw command tokens.

## Changes

### `mini_agent/durable_events.py`
- Added `SHELL_COMMAND_STARTED`, `SHELL_COMMAND_FINISHED`, `SHELL_COMMAND_ERROR`, `SHELL_COMMAND_BLOCKED` constants
- Added all four to `VALID_EVENT_TYPES`

### `mini_agent/shell.py`
- Added `event_store` parameter to `ShellRunner.__init__`
- Added `_record_shell_event()` helper — failure-isolated, records safe payload from allowlisted parsed argv only
- Instrumented `run()`:
  - `BLOCKED` with `disallowed_command` when command not in allowlist
  - `BLOCKED` with `cancelled` when user denies confirmation
  - `STARTED` after allowlist + confirmation pass, before subprocess execution
  - `FINISHED` with exit_code, stdout_bytes, stderr_bytes on subprocess completion (including nonzero exit)
  - `ERROR` with `timeout` label on `TimeoutExpired`
  - `ERROR` with `os_error` label on `OSError`

### `mini_agent/toolkits/registry_builder.py`
- Wires `durable_event_store` into `shell_runner` after creation

### `tests/test_durable_events.py`
- Added `ShellCommandDurableEventTests` class with 15 tests:
  - `test_successful_command_records_started_and_finished`
  - `test_disallowed_command_records_blocked`
  - `test_cancelled_command_records_blocked`
  - `test_timeout_records_error_with_allowed_command`
  - `test_nonzero_exit_still_records_finished`
  - `test_no_raw_command_in_payload`
  - `test_no_raw_output_in_serialized_events`
  - `test_no_raw_timeout_output_in_serialized_events`
  - `test_no_raw_os_error_in_serialized_events`
  - `test_malformed_blocked_command_records_without_raw_command`
  - `test_failure_isolation_broken_event_store`
  - `test_no_event_store_does_not_break_shell`
  - `test_shell_event_no_task_id`
  - `test_payload_has_executable_and_argv_count`
  - `test_default_registry_wires_shell_events`

## Payload Shape

```json
{
  "executable": "python3",
  "argv_count": 6,
  "status": "finished",
  "exit_code": 0,
  "timeout": false,
  "stdout_bytes": 1234,
  "stderr_bytes": 0,
  "error": ""
}
```

## Verification

```
$ python3 -m unittest tests.test_durable_events tests.test_mini_agent
Ran 203 tests — OK

$ python3 evals/run_evals.py
103 passed, 0 failed

$ python3 -m unittest tests.test_durable_events.ShellCommandDurableEventTests
Ran 15 tests — OK

$ python3 -m unittest discover -s tests
Ran 1183 tests — OK

$ git diff --check
OK
```

## Diff

```
 mini_agent/durable_events.py            |   8 ++
 mini_agent/shell.py                     |  87 +++++++++++++-
 mini_agent/toolkits/registry_builder.py |   1 +
 tests/test_durable_events.py            | 206 ++++++++++++++++++++++++++++++++
 4 files changed, 302 insertions(+), 2 deletions(-)
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- Scope limited to `ShellRunner.run` only; `Diagnostics.run_tests` not instrumented (separate future task).
