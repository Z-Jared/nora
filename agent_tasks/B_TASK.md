# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-018: eval coverage for durable test-run event logging.

## Instructions

TASK-017 is complete and approved. Add deterministic offline eval coverage for durable test-run events in `evals/run_evals.py`.

Add eval cases for:

1. Successful test run:
   - Exercise allowed `python3 -m unittest discover -s tests` in a temp project.
   - Verify durable event log records started/finished events with safe test metadata.

2. Failing test run:
   - Exercise a deterministic failing unittest.
   - Verify finished event records nonzero exit_code without raw failure body or traceback.

3. Blocked command:
   - Exercise a disallowed command.
   - Verify blocked event is emitted and no started/finished event is recorded.

4. Timeout or execution error:
   - Exercise timeout and/or patched `OSError`.
   - Verify error event is emitted while preserving existing operation behavior.

5. Failure isolation:
   - Broken/null event store should not change existing diagnostics behavior.

6. Safety assertions:
   - Use sentinel strings that would fail the eval if raw stdout/stderr, traceback text, raw exception text, reason text, full command text, or secret-like values are persisted in durable event payloads or serialized records.

Keep evals offline and deterministic. Do not call live LLM APIs and do not reimplement TASK-017 runtime behavior in eval-only code.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent
```

## Context

- TASK-017 added `TEST_RUN_STARTED`, `TEST_RUN_FINISHED`, `TEST_RUN_ERROR`, and `TEST_RUN_BLOCKED`.
- `evals/run_evals.py` already has durable event lifecycle, tool-call, model-call, file-edit, and shell-command event evals.
- Keep this task eval-only. Runtime changes belong to TASK-017 and should not be duplicated here.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
