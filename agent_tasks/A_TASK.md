# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-026: durable task registry action events.

Nora now has a queryable durable event log, but durable task CRUD/control operations performed through registry tools are not yet consistently audited as durable events. Add safe event logging around the durable task registry tools so the PM/runtime can answer who created, changed, retried, or deleted durable tasks without exposing raw task content.

## Scope

Update `mini_agent/toolkits/registry_builder.py` and supporting code/tests as needed.

1. Record durable events for registry durable task actions:
   - `create_durable_task` records `TASK_CREATED`.
   - `update_durable_task` records `TASK_STATUS_CHANGED`.
   - `retry_durable_task` records `TASK_RETRIED`.
   - `delete_durable_task` records an auditable task deletion event. Prefer a clear new event type only if needed; otherwise use an existing task lifecycle event with an explicit safe `operation`.

2. Event safety requirements:
   - Do not persist raw `goal`, raw step text, raw `steps`, raw failure reason, raw prompt/content, or secret-like values in event payloads or summaries.
   - Payloads should contain bounded metadata only, for example `operation`, `status`, `previous_status`, `step_count`, `retry_count`, `max_retries`, `failure_reason_present`, and `deleted`.
   - Include `task_id`, `source`, and `severity` consistently.
   - Event write failures must not change registry tool behavior.

3. Keep behavior backward-compatible:
   - Existing registry tool return JSON must remain unchanged except for intentional task state changes.
   - Existing `DurableTaskStore` storage semantics and transition validation should not be weakened.
   - Do not add eval coverage in this task.

## Suggested Tests

Add focused unit coverage in `tests/test_durable_tasks.py` and/or `tests/test_durable_events.py`:

1. `create_durable_task` emits one safe task-created event.
2. `update_durable_task` emits safe status-change metadata and records previous/new status.
3. `retry_durable_task` emits safe retry metadata and increments retry count as before.
4. `delete_durable_task` emits an auditable deletion event without raw task content.
5. Broken event store does not break create/update/retry/delete registry tools.
6. Serialized event safety: sentinel goal/steps/failure reason/secret strings are absent from event payloads, summaries, and `event.to_dict()`.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If registry behavior changes broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
