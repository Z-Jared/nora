# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-023: durable handoff event logging.

Nora is moving toward an Agent OS / Durable Runtime. Handoff artifacts should become auditable durable events so future agents can see when a task was packaged for continuation and when a prior task history item was restored.

## Scope

Add a narrow vertical slice for handoff lifecycle events around the existing task history handoff path.

1. Add event constants in `mini_agent/durable_events.py`:
   - `HANDOFF_CREATED`
   - `HANDOFF_ACCEPTED`
   - Include them in valid event type validation.

2. Instrument `mini_agent/task_runner.py`:
   - `TaskManager.finish(...)` should record `HANDOFF_CREATED` after the task is appended to history.
   - `TaskManager.restore(...)` should record `HANDOFF_ACCEPTED` after a task history item is restored into the active task slot.
   - Reuse the existing event-store failure isolation pattern.
   - Preserve the existing user-visible return strings as much as possible.

3. Keep the task narrow:
   - Do not create a new handoff file format.
   - Do not alter `agent_tasks/` worker workflow.
   - Do not implement replay/resume UI.
   - Do not add eval coverage in this task.

## Payload Requirements

Event payloads must contain safe metadata only. Good examples:

- artifact_type, e.g. `task_history`
- history_id, e.g. `task_1`
- status: created / accepted
- step_count
- done_step_count
- blocked_step_count
- summary_present boolean
- restored_from_present boolean

Do not store:

- raw goal text
- raw task summary text
- raw step text
- raw note text
- raw task history JSON
- raw user prompt or model output
- API keys or secret-like values
- unbounded strings

Event writes must be failure-isolated. A broken durable event store must not change task finish/restore behavior.

Existing `task_finished` / `task_status_changed` events may still contain their current payloads; this task's new handoff events must use safe metadata only.

## Suggested Tests

Add focused unit coverage in `tests/test_durable_events.py`, `tests/test_task_runner.py`, and/or existing registry tests:

1. `finish_task` emits `HANDOFF_CREATED` with safe metadata and preserves the existing finish result.
2. `restore_task` emits `HANDOFF_ACCEPTED` with safe metadata and preserves existing restore behavior.
3. Full serialized handoff events do not contain sentinel goal text, summary text, step text, note text, or secret-like values.
4. Broken event store does not break finish or restore.
5. Direct `TaskManager(...)` without an event store still behaves as before.
6. Default registry task tools emit the handoff events through the existing `TaskManager` wiring.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_events tests.test_task_runner tests.test_durable_tasks tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If task state behavior changes broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
