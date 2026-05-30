# Claude B Completion Report - TASK-016

Status: ready for Codex review

## Summary

Added 5 deterministic offline eval cases for durable shell-command event logging (TASK-015 runtime at b1794fa). Codex PM tightened the candidate with explicit forbidden payload-key checks and a safe allowed-arg sentinel case.

1. **shell_command_event_success** — Exercises `pwd` via `ShellRunner`. Verifies `SHELL_COMMAND_STARTED` → `SHELL_COMMAND_FINISHED` with `executable`, `exit_code=0`, `stdout_bytes>0`, `severity=info`, `task_id=None`.

2. **shell_command_event_blocked** — Exercises `rm -rf /`. Verifies `SHELL_COMMAND_BLOCKED` with `error=disallowed_command`, no started/finished events. Runs a second malformed command with sentinel arg to assert raw command text absent from serialized events.

3. **shell_command_event_cancelled** — Exercises confirmation denial via `confirm_action=lambda _: False`. Verifies `SHELL_COMMAND_BLOCKED` with `error=cancelled`, no started or finished events.

4. **shell_command_event_error** — Two sub-cases:
   - **Timeout**: Sleeps 30s script with 1s timeout. Verifies `SHELL_COMMAND_ERROR` with `status=timeout`, `timeout=True`. Asserts sentinel stdout content absent from serialized events.
   - **OSError**: Patches `subprocess.run` to raise `OSError(sentinel)`. Verifies `SHELL_COMMAND_ERROR` with `error=os_error`. Asserts sentinel OSError text absent from both user-visible result and serialized events.

5. **shell_command_event_failure_isolation** — Broken event store and `event_store=None` both must not break shell execution.

## Safety Assertions

All evals use named sentinels and assert absence from `event.to_dict()` serialized output:
- `_SHELL_SENTINEL_CMD` — raw command path/arg
- `_SHELL_SENTINEL_OUTPUT` — raw stdout content
- `os_sentinel` — raw OSError text
- Forbidden payload keys: no `stdout`, `stderr`, `command`, `args`, `argv`, `output`, `result`, `reason`, `exception`, or `traceback` keys stored

## Diff

```text
 evals/run_evals.py | 215 ++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 214 insertions(+), 1 deletion(-)
```

## Tests

```text
python3 evals/run_evals.py
108 passed, 0 failed

python3 -m unittest tests.test_durable_events tests.test_mini_agent
Ran 203 tests — OK

git diff --check
OK
```

## Notes

- No runtime code changed (TASK-015 was already complete at b1794fa).
- No fallback imports or shims added.
- Eval count increased from 103 to 108.
- No commit or push performed.
