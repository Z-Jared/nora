# Claude A Completion Report

Owner: Claude A
Task: TASK-030 — Durable worker registry v1
Status: done

## Summary

Implemented a minimal durable worker registry so PM/runtime can inspect worker identity, role, status, current task assignment, and workspace path.

**New module** `mini_agent/durable_workers.py`:
- `DurableWorker` dataclass: `worker_id`, `role`, `status`, `current_task_id`, `workspace_path`, `created_at`, `updated_at`, `last_seen_at`.
- `WorkerStatus` enum: `idle`, `assigned`, `running`, `paused`, `offline`.
- `DurableWorkerStore` with SQLite and JSONL backends: `register_worker` (upsert), `get_worker`, `list_workers`, `update_status`, `touch`.

**Registry tools** (`mini_agent/toolkits/registry_builder.py`):
- `register_worker` — register or update a worker (strips worker_id, rejects empty).
- `list_workers` — list registered workers.
- `get_worker` — get worker by id.
- `update_worker_status` — update status and optionally set `current_task_id`.

**25 new tests** in `tests/test_durable_workers.py`:
- SQLite: register/get, upsert, list, update status, clear task, unknown returns None, touch, round-trip.
- JSONL: register/get, list, update status, upsert.
- Registry tools: register, list, get, update, empty/whitespace id errors, invalid status error, update does not mutate durable task, durable task assignment still works.

## Diff Stat

```
 mini_agent/durable_workers.py           | 256 ++++++++++++++++++++++++++++++++
 mini_agent/toolkits/registry_builder.py | 120 +++++++++++++++++
 tests/test_durable_workers.py           | 245 ++++++++++++++++++++++++++++++
 3 files changed, 621 insertions(+)
```

## Checks Run

```
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
# 427 tests OK

python3 evals/run_evals.py
# 143 passed, 0 failed

git diff --check -- mini_agent/ tests/
# clean
```

## Known Risks / Limitations

- `register_worker` upserts: re-registering updates role/workspace_path but preserves status unless explicitly changed.
- No scheduling or worktree isolation implemented yet.
- No durable event logging for worker operations (not requested).
- No eval coverage added per task instruction.
