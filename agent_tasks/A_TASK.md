# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-028: durable task worker assignment metadata.

Nora's durable tasks already have a `worker_id` field, and durable events can now be filtered by `worker_id`, but the registry task tools do not expose worker assignment as a first-class runtime operation. Add a narrow worker-assignment layer so PM/runtime can answer which worker owns a durable task and query task-action events by that worker.

## Scope

Update `mini_agent/toolkits/registry_builder.py` and focused tests.

1. Expose worker ownership in durable task registry tools:
   - `create_durable_task` accepts optional `worker_id` and stores it on the created `DurableTask`.
   - Add an `assign_durable_task` registry tool that updates a task's `worker_id` without changing task status.
   - `list_durable_tasks` summary includes `worker_id`.
   - `get_durable_task` behavior stays backward-compatible.

2. Event linkage:
   - Registry task action events from TASK-026 should set top-level `worker_id` when the task has an assigned worker.
   - Assignment should record a safe durable event using an existing task lifecycle event type, with payload metadata such as `operation`, `task_id`, `worker_id_present`, and `previous_worker_id_present`.
   - Do not persist raw goal, raw step text, raw note/summary, or secret-like values in event payloads or summaries.

3. Compatibility and safety:
   - Existing callers that omit `worker_id` must behave exactly as before.
   - Unknown `task_id` returns the same JSON error style as existing durable task tools.
   - Empty/whitespace `worker_id` should clear assignment or be rejected explicitly; pick one behavior and test it.
   - Event write failures must not change create/assign/update/retry/delete behavior.
   - Keep this task narrow; do not build scheduler/worktree isolation yet.
   - Do not add eval coverage in this task.

## Suggested Tests

Add focused unit coverage in `tests/test_durable_tasks.py` and/or `tests/test_durable_events.py`:

1. `create_durable_task(worker_id=...)` persists worker ownership and `list_durable_tasks` includes it.
2. `assign_durable_task` sets or clears worker ownership and returns the updated task JSON.
3. Unknown task assignment returns an error JSON.
4. Task action events include top-level `worker_id` after assignment.
5. Assignment emits a safe event without raw task content.
6. Broken event store does not break assignment.
7. Existing create/list/update/retry/delete tests still pass without `worker_id`.

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
