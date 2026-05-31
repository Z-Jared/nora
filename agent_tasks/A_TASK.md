# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-025: durable event query filters.

Nora is moving toward an Agent OS / Durable Runtime. The event log now records many lifecycle events; the next step is making those events queryable by the dimensions a PM/reviewer/runtime needs for auditing.

## Scope

Add filter support to durable event listing, preserving existing behavior.

1. Extend `mini_agent/durable_events.py` `DurableEventStore.list_events(...)`:
   - Keep existing `task_id` and `max_results` behavior backward-compatible.
   - Add optional filters:
     - `event_type`
     - `source`
     - `severity`
     - `worker_id`
     - `trace_id`
     - `checkpoint_id`
   - Support both SQLite and JSONL backends.
   - Return newest-first, still clamped to max 500.
   - Use parameterized SQL for SQLite.

2. Update `mini_agent/toolkits/registry_builder.py`:
   - Expose the new filters on the `list_durable_events` registry tool.
   - Include `source` and `severity` in each returned event summary.
   - Preserve existing callers that only pass `task_id` or `max_results`.

3. Keep the task narrow:
   - Do not change event recording behavior.
   - Do not add new event types.
   - Do not change `get_durable_event`.
   - Do not add eval coverage in this task.

## Safety / Compatibility Requirements

- Filtering must not load or expose payloads through `list_durable_events`; summaries remain bounded metadata.
- Invalid/empty filters should behave like no filter after stripping whitespace.
- Filtering by one dimension should compose with `task_id` and `max_results`.
- Existing tests and evals must continue to pass.

## Suggested Tests

Add focused unit coverage in `tests/test_durable_events.py` and/or existing registry tests:

1. SQLite backend filters by `event_type`, `source`, `severity`, `worker_id`, `trace_id`, and `checkpoint_id`.
2. JSONL backend supports the same filters.
3. Combined filters narrow results correctly.
4. `max_results` is still clamped and newest-first.
5. `list_durable_events` registry tool accepts the new filters and includes `source`/`severity` in its summary output.
6. Backward compatibility: existing `list_events(task_id=..., max_results=...)` and registry calls still work.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If event-store behavior changes broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
