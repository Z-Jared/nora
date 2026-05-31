# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-024: eval coverage for durable handoff event logging.

## Instructions

TASK-023 is complete and approved. Add deterministic offline eval coverage for durable handoff events in `evals/run_evals.py`.

Add eval cases for:

1. Handoff created:
   - Exercise task finish through `TaskManager` or the default registry task tools.
   - Verify `HANDOFF_CREATED` is recorded with safe metadata.

2. Handoff accepted:
   - Finish a task into history, then restore it.
   - Verify `HANDOFF_ACCEPTED` is recorded with safe metadata.

3. Safety assertions:
   - Use sentinel strings for raw goal, summary, step text, note text, and a secret-like value.
   - Verify those sentinels are absent from event payloads, summaries, and full serialized `event.to_dict()` output for handoff events.
   - Check forbidden payload keys such as `goal`, `summary`, `steps`, `step_text`, `note`, `history_json`, `raw`, `prompt`, `content`, and `secret`.

4. Failure isolation:
   - Broken/null event store should not change finish or restore behavior.

5. Registry wiring:
   - Through `build_default_registry`, verify task tools produce handoff events via the same durable event store.

Keep evals offline and deterministic. Do not call live LLM APIs and do not reimplement TASK-023 runtime behavior in eval-only code. If you find a real runtime bug while writing evals, stop and report it in `agent_tasks/B_DONE.md` instead of silently changing runtime code.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_task_runner tests.test_durable_tasks tests.test_mini_agent
git diff --check
```

## Context

- TASK-023 added `HANDOFF_CREATED` and `HANDOFF_ACCEPTED`.
- Runtime tests already cover handoff durable events in `tests/test_durable_events.py`.
- `evals/run_evals.py` already has durable event lifecycle, tool-call, model-call, file-edit, shell-command, test-run, approval, and review-gate event evals.
- Keep this task eval-only. Runtime changes belong to TASK-023 and should not be duplicated here.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
