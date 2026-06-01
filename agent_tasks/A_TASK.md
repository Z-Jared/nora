# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-058: Durable task timeline inspection tool v1.

Nora now records durable events for task actions, checkpoints, lifecycle controls, recovery plans, and many tool/runtime operations. The next small replay/recovery step is a read-only registry tool that returns a safe chronological task timeline for inspection.

## Scope

Build only timeline inspection. Do not implement replay execution, worker process execution, worktree creation, patch queues, broad schema redesign, or automatic task mutation.

1. Add a read-only registry tool:
   - Suggested name: `get_durable_task_timeline(task_id, limit=50)`
   - Register near existing durable event/task registry tools in `mini_agent/toolkits/registry_builder.py`.
   - Unknown task ids should return JSON `{"error": ...}`.
   - `limit` should be bounded to an integer range, suggested `1..200`; non-integer limit should return JSON error without crashing.
   - This tool should use read-only task/event permission semantics.

2. Timeline semantics:
   - Fetch durable events for the task using existing `DurableEventStore.list_events(task_id=...)`.
   - Return events in chronological order, oldest first.
   - Apply the bounded limit after ordering so output is deterministic.
   - Include a bounded task summary:
     - `task_id`
     - `status`
     - `event_count`
     - `returned_event_count`
     - `checkpoint_count`
     - `trace_ref_count`
     - `worker_id_present`
   - Include event summaries with only safe metadata:
     - `event_id`
     - `event_type`
     - `created_at`
     - `source`
     - `severity`
     - `checkpoint_id`
     - `checkpoint_id_present`
     - `trace_id_present`
     - `worker_id_present`
     - `summary_present`
     - `payload_key_count`
     - `payload_keys` (sorted safe key names only; no values)

3. Safety and behavior:
   - Do not return raw task goal, raw step text, notes, summaries, checkpoint descriptions, raw `state_snapshot`, raw payload values, prompts, diffs, shell output, env vars, request strings, or secret-like values.
   - Do not mutate task state or event state.
   - If the event store fails, return a bounded JSON error; do not crash.
   - Existing `list_durable_events` and `get_durable_task` behavior must remain unchanged.

4. Compatibility:
   - Do not mutate durable task state.
   - Preserve existing behavior of `get_durable_task`, `list_durable_tasks`, `list_durable_events`, recovery planning, lifecycle controls, and checkpoint creation.
   - Preserve all TASK-054 through TASK-057 tests.

5. Tests:
   - Add focused tests in `tests/test_durable_tasks.py` and/or `tests/test_durable_events.py`.
   - Cover chronological timeline output over create/checkpoint/recovery events.
   - Cover checkpoint_id linkage appears only as safe id metadata.
   - Cover `payload_keys` contains key names but no raw payload values.
   - Cover limit bounding and non-integer limit error.
   - Cover unknown task error.
   - Cover safe output and no raw goal/step/note/summary/checkpoint description/state_snapshot/secret leakage.
   - Cover no task state mutation.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared registry builder paths broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
