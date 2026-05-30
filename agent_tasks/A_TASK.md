# Claude A Task

Owner: Claude A
Status: assigned

## Goal

Implement TASK-015: durable shell-command event logging.

Nora is moving toward an Agent OS / Durable Runtime. Shell command execution must become auditable durable lifecycle events, like task/tool/model/file-edit events, without storing raw command output, secret-bearing command text, or unbounded data.

## Scope

Add durable event logging for shell-command execution:

1. Add event constants in `mini_agent/durable_events.py`:
   - `SHELL_COMMAND_STARTED`
   - `SHELL_COMMAND_FINISHED`
   - `SHELL_COMMAND_ERROR`
   - `SHELL_COMMAND_BLOCKED`
   - Include them in valid event type validation.

2. Hook lifecycle events in `mini_agent/shell.py` `ShellRunner.run`.
   - blocked: unsafe/disallowed command, confirmation cancellation
   - started: after allowlist parsing succeeds and before execution attempt
   - finished: subprocess completed normally, regardless of nonzero exit code
   - error: timeout or `OSError`

3. Wire `DurableEventStore` into `ShellRunner` through `mini_agent/toolkits/registry_builder.py`.
   - Keep direct `ShellRunner(...)` use compatible when no event store is supplied.

## Payload Requirements

Event payloads must contain safe metadata only. Good examples:

- executable name or command kind
- argv count
- status
- exit_code
- timeout flag
- stdout/stderr byte counts or char counts
- generic error/block reason

Do not store:

- raw stdout or stderr
- raw full command string if it may contain secrets
- raw shell arguments that may contain secrets
- raw exception text
- secrets or sentinel secret strings
- unbounded output

Event writes must be failure-isolated. A broken durable event store must not change existing shell command behavior.

Keep this task narrow. Do not instrument `Diagnostics.run_tests` yet; test-run events are a separate future task.

## Suggested Tests

Add focused coverage in `tests/test_durable_events.py` and/or existing shell tests:

1. Successful `pwd` or `python3 -m unittest discover -s tests` emits started + finished with safe metadata.
2. Disallowed command such as `rm -rf /` emits blocked and does not emit finished.
3. Confirmation cancellation emits blocked and does not execute.
4. Timeout emits error with generic `timeout` label and no raw output.
5. `OSError` emits error with generic label and preserves existing return behavior.
6. Broken event store does not break shell command behavior.
7. Payload and serialized events do not contain sentinel command/output/error text.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
```

If shared registry wiring or shell behavior changes broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```

Do not commit or push.
