# Claude B Task

Owner: Claude B
Status: waiting

## Goal

Prepare for TASK-016: eval coverage for durable shell-command event logging after Claude A completes TASK-015.

## Instructions

Do not start implementation until Codex PM explicitly dispatches this task after TASK-015 lands in the main worktree.

Once TASK-015 is complete, add deterministic offline eval coverage for durable shell-command events in `evals/run_evals.py`.

Add eval cases for:

1. Successful shell command:
   - Exercise an allowed command such as `pwd`.
   - Verify durable event log records started/finished events with safe command metadata.

2. Blocked command:
   - Exercise a disallowed/dangerous command.
   - Verify a blocked event is emitted and no finished event is recorded.

3. Cancelled command:
   - Exercise direct `ShellRunner` confirmation cancellation if registry-level confirmation would stop before runtime.
   - Verify cancelled/blocked semantics.

4. Timeout or execution error:
   - Exercise timeout or `OSError`.
   - Verify an error event is emitted while preserving existing operation behavior.

5. Failure isolation:
   - Broken event store should not change existing shell operation behavior.

6. Safety assertions:
   - Use sentinel strings that would fail the eval if raw command output, raw stderr/stdout, raw exception text, or secret-like command text is persisted in durable event payloads or serialized event records.

Keep evals offline and deterministic. Do not call live LLM APIs and do not reimplement TASK-015 runtime behavior in eval-only code.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_mini_agent
```

## Context

- TASK-015 is expected to add `SHELL_COMMAND_STARTED`, `SHELL_COMMAND_FINISHED`, `SHELL_COMMAND_ERROR`, and `SHELL_COMMAND_BLOCKED`.
- `evals/run_evals.py` already has durable event lifecycle, tool-call, model-call, and file-edit event evals.
- Keep this task eval-only. Runtime changes belong to TASK-015 and should not be duplicated here.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
