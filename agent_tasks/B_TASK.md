# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-027: eval coverage for durable event query filters.

TASK-025 added query filters to `DurableEventStore.list_events(...)` and the `list_durable_events` registry tool. Add deterministic offline eval coverage so future event-log changes cannot silently break PM/reviewer/runtime audit queries.

## Scope

Edit `evals/run_evals.py` only unless you discover a real runtime bug. If you find a runtime bug, stop and report it in `agent_tasks/B_DONE.md` instead of fixing runtime code in this task.

Add eval cases covering:

1. SQLite event query filters:
   - Filter by `event_type`, `source`, `severity`, `worker_id`, `trace_id`, and `checkpoint_id`.
   - Combined filters narrow results correctly.

2. JSONL event query filters:
   - At least `event_type`, `source` + `severity`, and `trace_id`/`checkpoint_id`.

3. Registry wiring:
   - `list_durable_events` accepts the new filters.
   - Registry output includes `source` and `severity`.
   - Registry output does not include `payload`.

4. Query semantics:
   - Filters compose with `task_id`.
   - Filtering happens before `max_results` slicing.
   - Results remain newest-first.
   - Empty/whitespace filters behave like no filter.

5. Safety:
   - Use sentinel payload strings and a secret-like value.
   - Verify `list_durable_events` summaries do not expose event payloads or sentinel values.

Keep evals offline and deterministic. Do not call live LLM APIs.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run the focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
