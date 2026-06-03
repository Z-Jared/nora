# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-081: Worker workspace merge closeout candidate query v1.

TASK-080 finalization is approved and pushed. Nora can now apply reviewed worker workspace changes, audit apply events, and finalize the durable task/worker/lease. The next step is a read-only PM queue tool that tells Codex which worker/task pairs are ready to finalize and why other pairs are not ready.

Do not implement auto-finalization, project-root writes, git commits, git pushes, shell execution, process isolation, Docker, UI changes, model routing, worker auto-start, workspace deletion, or eval changes in this task.

## Scope

1. Add a registry-level read-only tool near the worker workspace apply/audit/finalize section in `mini_agent/toolkits/registry_builder.py`.

   Suggested tool name:
   - `list_worker_workspace_merge_closeout_candidates(worker_id="", task_id="", limit=20)`

2. The tool should return bounded JSON only.

   Include safe metadata such as:
   - `candidates`: list
   - `count`
   - per candidate: `ready`, `reason`, `worker_id`, `task_id`, `lease_id`, `task_status`, `worker_status`, `workspace_released` if derivable, `latest_apply_event_id`, `latest_apply_created_at`

3. Candidate logic:
   - Respect optional `worker_id` and `task_id` filters.
   - Bound `limit` to 1..100; bad limit returns bounded JSON error.
   - Prefer current durable task/worker/workspace lease state over caller input.
   - A candidate is ready only when:
     - task exists and is assigned to the worker
     - task status is `running`
     - worker exists, is not offline/idle, and `current_task_id` matches
     - active workspace lease exists for the worker/task
     - there is at least one successful `workspace_merge_apply` event for the same worker/task/active lease id
   - Use safe reason labels for not-ready states, for example:
     - `ready_to_finalize`
     - `already_finalized`
     - `task_not_running`
     - `worker_unavailable`
     - `worker_task_mismatch`
     - `workspace_lease_invalid`
     - `no_successful_apply`

4. Safety:
   - Read-only: do not mutate task, worker, lease, review gate, project root, or worker workspace.
   - Do not release leases.
   - Do not call `finalize_worker_workspace_merge`.
   - Do not expose raw file content, raw patch text, task goal, steps, prompts, env vars, shell output, request strings, reviewer notes, raw exception strings, or secrets.
   - Sanitize event ids / lease ids / paths if needed using existing audit safety patterns.

5. Compatibility:
   - Preserve existing apply, audit, finalize, dry-run, summary, patch export, review gate, workspace lease, sandbox guard, read/list/preview/write, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.
   - Since Claude B is editing `evals/run_evals.py`, do not edit `evals/run_evals.py`.
   - If you discover a TASK-080 runtime bug that blocks this task, stop and write it in `agent_tasks/A_DONE.md`; do not broad-refactor.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` covering:

- Ready candidate after successful apply with active matching lease.
- No candidate / not-ready before apply.
- Stale apply event from a previous lease is not ready.
- Missing active lease is not ready.
- Completed task reports bounded `already_finalized` or is omitted consistently; document chosen behavior in DONE.
- Offline/idle/mismatched worker states are not ready.
- `worker_id`, `task_id`, and `limit` filters work; bad limit returns bounded JSON error.
- Query is read-only and does not mutate project root, worker workspace, task, worker, lease, or review gate.
- Output does not leak raw file content, patch text, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
- Existing apply/audit/finalize/dry-run/summary/patch/review gate/read/list/write/preview/claim/dispatch tools still behave after candidate query.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch durable event helpers broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
