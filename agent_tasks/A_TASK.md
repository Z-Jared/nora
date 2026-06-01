# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-048: Durable worker auto-dispatch v1.

Nora already has durable workers, worker heartbeat/offline lifecycle, task ownership metadata, and single-worker `claim_durable_task`. Add a narrow auto-dispatch layer that assigns pending durable tasks to available workers without launching processes or creating worktrees yet.

## Scope

Build only assignment automation. Do not spawn terminals, start agents, create git worktrees, implement sandboxing, or change task execution semantics in this task.

1. Add an auto-dispatch runtime path:
   - Suggested registry tool: `dispatch_durable_tasks`.
   - Finds available workers (`idle`/online and no current task).
   - Finds pending durable tasks with no `worker_id`.
   - Assigns oldest pending tasks to available workers, up to `max_assignments`.
   - Does not overwrite `assigned`, `running`, `paused`, or `offline` workers.
   - Does not change task status unless existing local semantics already require it; preserve current claim behavior if possible.

2. State updates:
   - Set task `worker_id`.
   - Set worker status/current assignment consistently.
   - Return bounded JSON with assignment summaries: worker_id, task_id, status, count.
   - Avoid returning raw task goals, full steps, prompts, or secrets.

3. Safety and failure isolation:
   - Broken event logging must not break assignment.
   - Invalid `max_assignments` should be bounded.
   - No assignments when no idle workers or no pending tasks.
   - Offline/stale workers must not receive tasks.

4. Tests:
   - Add focused tests, likely in `tests/test_durable_workers.py` and/or `tests/test_durable_tasks.py`.
   - Cover basic dispatch, multiple workers/tasks, max assignment cap, no available workers, no pending tasks, offline/running worker exclusion, existing assigned tasks untouched, bounded output, and event failure isolation.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
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
