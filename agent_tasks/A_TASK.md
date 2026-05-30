# Claude A Task

Owner: Claude A
Status: assigned

## Goal

Implement TASK-017: durable test-run event logging.

Nora is moving toward an Agent OS / Durable Runtime. Test execution should be auditable as first-class durable lifecycle events, without storing raw test output, tracebacks, exception strings, or unbounded data.

## Scope

Add durable event logging for `Diagnostics.run_tests`:

1. Add event constants in `mini_agent/durable_events.py`:
   - `TEST_RUN_STARTED`
   - `TEST_RUN_FINISHED`
   - `TEST_RUN_ERROR`
   - `TEST_RUN_BLOCKED`
   - Include them in valid event type validation.

2. Hook lifecycle events in `mini_agent/diagnostics.py` `Diagnostics.run_tests`.
   - blocked: command rejected by the test allowlist
   - started: after allowlist passes, before subprocess execution
   - finished: subprocess completed normally, including nonzero exit codes
   - error: timeout or `OSError`

3. Wire `DurableEventStore` into `Diagnostics` through `mini_agent/toolkits/registry_builder.py`.
   - Keep direct `Diagnostics(...)` use compatible when no event store is supplied.

## Payload Requirements

Event payloads must contain safe metadata only. Good examples:

- test command kind, e.g. `unittest_discover`
- status
- exit_code
- timeout flag
- stdout/stderr byte counts or char counts
- max_output_chars
- generic error/block reason

Do not store:

- raw stdout or stderr
- raw traceback or failure body
- raw full command string or raw shell args
- raw exception text
- reason text
- secrets or sentinel strings
- unbounded output

Event writes must be failure-isolated. A broken durable event store must not change existing test-run behavior.

Keep this task narrow. Do not change shell-command events, evals, retry logic, or repair-loop behavior beyond preserving existing `Diagnostics.run_tests` output semantics.

## Suggested Tests

Add focused coverage in `tests/test_durable_events.py` and/or existing diagnostics tests:

1. Successful allowed test run emits started + finished with safe metadata.
2. Failing tests still emit finished with nonzero exit_code.
3. Rejected command emits blocked and no started/finished.
4. Timeout emits error with generic `timeout` label and no raw output.
5. `OSError` emits error with generic label and no raw exception text in events.
6. Broken event store does not break `run_tests`.
7. Payload and serialized events do not contain sentinel stdout/stderr/traceback/exception/reason/command text.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent
python3 evals/run_evals.py
```

If registry wiring or diagnostics behavior changes broadly, also run:

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
