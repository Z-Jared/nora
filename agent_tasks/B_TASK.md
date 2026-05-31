# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-020: eval coverage for durable approval event logging.

## Instructions

TASK-019 is complete and approved. Add deterministic offline eval coverage for durable approval events in `evals/run_evals.py`.

Add eval cases for:

1. Approved permissioned tool:
   - Exercise a permissioned tool with `confirm_action=lambda _: True`.
   - Verify approval requested + decided events are recorded.
   - Verify decided status is approved and existing tool behavior still succeeds.

2. Denied permissioned tool:
   - Exercise a permissioned tool with `confirm_action=lambda _: False`.
   - Verify approval requested + decided events are recorded.
   - Verify decided status is denied, severity is warning, and cancellation result remains `已取消操作。`.

3. Non-permissioned tool:
   - Exercise a read/non-confirmation tool.
   - Verify no approval events are emitted.

4. Failure isolation:
   - Broken/null event store should not change approved or denied confirmation behavior.

5. Safety assertions:
   - Use sentinel strings that would fail the eval if raw argument values, commit/message content, reason text, confirmation prompt text, or secret-like values are persisted in durable event payloads, summaries, or serialized records.
   - Check forbidden payload keys such as `args`, `arguments`, `message`, `reason`, `prompt`, `raw_args`, `content`, `secret`, and `command`.

Keep evals offline and deterministic. Do not call live LLM APIs and do not reimplement TASK-019 runtime behavior in eval-only code. If you find a real runtime bug while writing evals, stop and report it in `agent_tasks/B_DONE.md` instead of silently changing runtime code.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent
git diff --check
```

## Context

- TASK-019 added `APPROVAL_REQUESTED` and `APPROVAL_DECIDED`.
- Runtime tests already cover approval durable events in `tests/test_durable_events.py`.
- `evals/run_evals.py` already has durable event lifecycle, tool-call, model-call, file-edit, shell-command, and test-run event evals.
- Keep this task eval-only. Runtime changes belong to TASK-019 and should not be duplicated here.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
