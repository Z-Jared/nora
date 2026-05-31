# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-034: durable worker task claim v1.

Nora now tracks durable workers and their liveness, but there is still no minimal scheduler primitive for a worker to claim available work. Add a narrow claim tool that lets a registered online worker claim the oldest pending, unassigned durable task and updates both task ownership and worker runtime state.

## Scope

Build narrowly in `mini_agent/toolkits/registry_builder.py`, using existing `DurableTaskStore` and `DurableWorkerStore` APIs. Add store helpers only if they keep the implementation simpler and well tested.

1. Add a registry tool such as `claim_durable_task(worker_id)`:
   - `worker_id` is required and stripped.
   - Unknown worker returns a JSON error.
   - Offline worker returns a JSON error.
   - If the worker already has `current_task_id`, return that assignment instead of claiming a second task.
   - Select the oldest pending durable task whose `worker_id` is empty.
   - Assign the task to the worker without changing task status.
   - Update the worker to `status="assigned"` and `current_task_id=<task_id>`.
   - If no pending unassigned task exists, return a JSON object with `claimed: false` and no mutation.

2. Durable event behavior:
   - Record a safe task action event for successful claims, using the existing task action event style.
   - Payload must include safe metadata only, such as `operation="claim"`, `task_id`, `worker_id_present`, and previous worker/task presence booleans.
   - Event write failure must not prevent the claim.

3. Safety and compatibility:
   - Do not run or execute the task.
   - Do not create worktrees.
   - Do not change durable task status transition rules.
   - Do not expose raw task goal, steps, worker paths, prompts, env vars, or secrets in claim event payloads.

## Suggested Tests

Add focused tests, likely in `tests/test_durable_workers.py` or `tests/test_durable_events.py`:

1. Registered idle worker claims oldest pending unassigned task.
2. Claim updates task `worker_id` and worker `status/current_task_id`.
3. Claim does not change durable task status.
4. Unknown worker and offline worker return JSON errors.
5. Worker with existing `current_task_id` does not claim a second task.
6. No available task returns `claimed: false` without mutation.
7. Claim emits safe event and does not leak raw task goal/step/secret.
8. Broken event store does not prevent claim.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared task/event logic broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
