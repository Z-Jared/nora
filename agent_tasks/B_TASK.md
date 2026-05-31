# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-029: eval coverage for durable task action events.

TASK-026 added durable events for durable task registry actions. Add deterministic offline eval coverage so future runtime changes cannot silently stop auditing create/update/retry/delete task operations or leak raw task content into those events.

## Scope

Edit `evals/run_evals.py` only unless you discover a real runtime bug. If you find a runtime bug, stop and report it in `agent_tasks/B_DONE.md` instead of fixing runtime code in this task.

Add eval cases covering:

1. Task action event creation:
   - `create_durable_task` emits `TASK_CREATED`.
   - `update_durable_task` emits `TASK_STATUS_CHANGED` with `previous_status` and new `status`.
   - `retry_durable_task` emits `TASK_RETRIED`.
   - `delete_durable_task` emits an auditable delete event.

2. Registry/event query wiring:
   - Use `list_durable_events` to query these events by `task_id` and `event_type`.
   - Verify source/severity are present and payload is not exposed by `list_durable_events`.

3. Safety assertions:
   - Use sentinel strings for raw goal, raw step text, raw failure reason, and a secret-like value.
   - Assert those sentinels are absent from serialized task-action events and from `list_durable_events` output.
   - Check forbidden payload keys such as `goal`, `steps`, `step_text`, `failure_reason`, `raw`, `prompt`, `content`, and `secret`.

4. Failure isolation:
   - Broken event store must not change create/update/retry/delete registry tool behavior.

Keep evals offline and deterministic. Do not call live LLM APIs.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_durable_tasks tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run the focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
