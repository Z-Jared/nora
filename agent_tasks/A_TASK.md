# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-093: Worker lifecycle scheduler blocker explanation v1

## Goal

Add a read-only scheduler explanation tool that answers: "why is worker lifecycle work not moving, and what would the scheduler do next?"

Suggested tool name:

`explain_worker_lifecycle_scheduler_state(worker_id="", task_id="", limit=20)`

## Requirements

- Register the tool in the default registry.
- Permission must be read-only: `task/read`, `requires_confirmation=False`.
- Do not mutate durable task, worker, workspace lease, event, filesystem, project root, worker workspace, shell, git, browser, process, or network state.
- Reuse existing state/query helpers where possible:
  - worker/task stores
  - active workspace lease state
  - `plan_worker_lifecycle_actions`
  - `list_worker_workspace_merge_closeout_candidates`
  - existing scheduler reason labels from run-once/tick/loop
- Inputs:
  - `worker_id`: optional string filter, default empty.
  - `task_id`: optional string filter, default empty.
  - `limit`: integer only, default 20, clamp 1..100, reject bool/float/string with bounded error JSON.
  - Reject non-string `worker_id`/`task_id` with bounded error JSON.
- Output bounded JSON with at least:
  - `scheduler`: `worker_lifecycle`
  - `filters`
  - `limit`
  - `summary`
  - `workers`
  - `tasks`
  - `closeout_candidates`
  - `planned_actions`
  - `blocked_reasons`
  - `next_actions`
- Use stable reason labels. Include labels for relevant states such as:
  - `ready_closeout`
  - `waiting_for_workspace_merge_apply`
  - `missing_active_lease`
  - `worker_offline`
  - `worker_idle`
  - `worker_running`
  - `pending_task_unassigned`
  - `dispatch_available`
  - `dispatch_blocked_in_scheduler`
  - `already_finalized`
  - `task_not_running`
  - `task_worker_mismatch`
  - `no_pending_tasks`
  - `no_idle_workers`
  - `no_action_needed`
- Explainability expectations:
  - For running worker/task with approved applied workspace merge, report ready closeout and next action finalize.
  - For running worker/task without merge apply, report wait/missing apply reason.
  - For pending unassigned task + idle worker, report dispatch available but blocked by current guarded scheduler policy unless this tool is explicitly read-only planning.
  - For idle worker without pending tasks, report no pending tasks.
  - For pending tasks without idle workers, report no idle workers.
  - For offline worker, report worker_offline and no unsafe action.
- Safety/no-leak:
  - Do not include task goals, steps, notes, prompts, file contents, raw diffs, reviewer summaries, workspace paths, project-root paths, shell/env/request strings, or secrets.
  - Include only safe ids, statuses, reason labels, counts, timestamps when already safe, and bounded metadata.
- Keep output compact and deterministic. Sort workers/tasks/actions by stable ids or creation timestamps.

## Tests

Add focused unit tests, preferably in `tests/test_durable_workers.py`, covering:

- Empty state returns no_action_needed / no pending / no idle summaries.
- Ready closeout explains ready finalize action without mutation.
- Not-ready closeout explains waiting/missing apply/lease reason.
- Pending task + idle worker explains dispatch availability and guarded block reason without dispatching.
- Pending task without idle worker explains no_idle_workers.
- Idle worker without pending task explains no_pending_tasks.
- Offline worker reports worker_offline and no unsafe action.
- `worker_id` and `task_id` filters.
- `limit` clamp and bad numeric/string filter args.
- Safety/no-leak for goal, steps, file content, reviewer, shell/env/request, workspace path, secrets.
- Permission is read-only and does not require confirmation.
- Compatibility with planner, scheduler tick, scheduler loop, run-once, closeout candidate query, worker/task registry, claim, and dispatch tools.

Run:

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecyclePlannerTests
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
git diff --check
```

## Boundaries

- Do not edit `agent_tasks/B_TASK.md` or `agent_tasks/B_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/A_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh A
```

## Notes

- Do not commit or push.
