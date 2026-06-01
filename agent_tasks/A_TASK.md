# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-050: Durable task lifecycle control tools v1.

Nora already has durable task status transitions and generic `update_durable_task`, but the runtime does not expose explicit, auditable lifecycle controls for pause/resume/cancel. Add narrow registry tools that make those lifecycle actions first-class while preserving the existing state machine and event safety.

## Scope

Build only lifecycle control tools. Do not spawn terminals, start agents, create git worktrees, implement worker process execution, or redesign the durable task schema in this task.

1. Add explicit registry tools:
   - `pause_durable_task(task_id, reason="")`
   - `resume_durable_task(task_id)`
   - `cancel_durable_task(task_id, reason="")`
   - Register them near the existing durable task registry tools in `mini_agent/toolkits/registry_builder.py`.
   - Use the existing `DurableTaskStore.update_status()` transition rules. Invalid transitions should return JSON `{"error": ...}` instead of raising through the registry.

2. Lifecycle semantics:
   - Pause: valid only where the existing store permits `running -> paused`.
   - Resume: use existing valid transitions back to `running` from paused/blocked.
   - Cancel: use existing valid transitions to `cancelled`.
   - Do not bypass `_VALID_TRANSITIONS`.
   - Do not persist raw pause/cancel `reason` text. Treat reason as presence metadata only.
   - Return bounded JSON summaries, not full `task.to_dict()`: include `task_id`, `status`, `previous_status`, `worker_id_present`, and `reason_present` where relevant. Do not return goal, steps, prompt text, raw reason, or failure body.

3. Worker consistency:
   - If a paused task has an existing worker whose `current_task_id` is this task, set worker status to `paused`.
   - If a resumed task has an existing non-offline worker whose `current_task_id` is this task, set worker status to `running`.
   - If a cancelled task has an existing worker whose `current_task_id` is this task, release that worker to `idle` with no current task.
   - Do not assign new workers, start workers, or create workspaces.
   - Worker update failures should not corrupt the task state. If you need to choose between simplicity and atomicity, keep the behavior explicit in tests and DONE notes.

4. Event logging and safety:
   - Record `TASK_STATUS_CHANGED` events with `operation` set to `pause`, `resume`, or `cancel`.
   - Include only safe metadata: `task_id`, `status`, `previous_status`, `worker_id_present`, `reason_present`.
   - Do not store raw goal, steps, prompts, raw reason text, shell output, diff, or secret-like values in event payload or summary.
   - Broken event logging must not prevent lifecycle operations.

5. Tests:
   - Add focused tests in `tests/test_durable_tasks.py` and/or `tests/test_durable_events.py`.
   - Cover successful pause/resume/cancel flows.
   - Cover invalid transitions and unknown task ids.
   - Cover worker status/current task consistency for pause/resume/cancel.
   - Cover bounded output and no raw reason/goal/steps leakage.
   - Cover event-store failure isolation.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_durable_workers tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared registry builder paths broadly or worker-store semantics, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
