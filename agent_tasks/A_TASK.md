# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-030: durable worker registry v1.

Nora now lets durable tasks carry `worker_id`, but workers themselves are still just strings. Add a minimal durable worker registry so PM/runtime can inspect worker identity, role, status, current task assignment, and workspace path as first-class runtime state.

## Scope

Implement a narrow worker registry. Prefer following the existing durable store style in `mini_agent/durable_tasks.py`.

1. Add durable worker data/storage:
   - Create a small module such as `mini_agent/durable_workers.py`.
   - Define a `DurableWorker` dataclass with at least:
     - `worker_id`
     - `role`
     - `status`
     - `current_task_id`
     - `workspace_path`
     - `created_at`
     - `updated_at`
     - `last_seen_at`
   - Support SQLite via `NoraDB` and JSONL fallback.
   - Provide focused store methods: upsert/register worker, get worker, list workers, update status/current task.

2. Add registry tools in `mini_agent/toolkits/registry_builder.py`:
   - `register_worker`
   - `list_workers`
   - `get_worker`
   - `update_worker_status`
   - Keep tool outputs bounded JSON summaries.

3. Safety and compatibility:
   - Do not change durable task status semantics.
   - Do not implement scheduling or worktree creation yet.
   - Do not expose environment variables, secrets, or raw prompts in worker records.
   - Existing tests/evals must continue to pass.
   - Worker ids should be stripped; empty ids should return a JSON error.

## Suggested Tests

Add focused unit tests, probably in a new `tests/test_durable_workers.py`:

1. SQLite store can register, get, list, and update a worker.
2. JSONL fallback supports the same basics.
3. Registry tools are registered and return expected JSON.
4. Empty worker id returns an error through registry tools.
5. Updating `current_task_id` does not mutate the durable task itself.
6. Existing durable task worker assignment tests still pass.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared registry wiring broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
