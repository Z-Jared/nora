# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-072: Worker workspace review gate artifact v1.

TASK-070 runtime and TASK-071 deterministic eval coverage are approved and visible in the worktree. Start implementation now.

Nora can now prepare worker workspaces, let workers edit only their leased workspace, and export safe change summaries/patches for Codex PM review. The next step is adding a review gate artifact that records whether a worker workspace output has been reviewed and approved/rejected before any future merge workflow.

Do not implement project-root merge, patch apply to project root, git worktrees, shell execution, process isolation, Docker, UI changes, or model routing in this task.

## Scope

1. Add minimal registry-level review gate tools near the existing worker workspace change export section in `mini_agent/toolkits/registry_builder.py`.

   Suggested tool names:
   - `record_worker_workspace_review_gate(worker_id, task_id, decision, reviewer="codex_pm", summary="", checks_passed=True, patch_exported=True)`
   - `get_worker_workspace_review_gate(worker_id, task_id)`

   If the existing durable event/review gate patterns suggest better names, keep the names clear and stable.

2. Reuse existing worker workspace validation:
   - Worker must exist.
   - Worker must not be offline or idle.
   - `worker.current_task_id == task_id`.
   - Task must exist.
   - `task.worker_id == worker_id`.
   - Active lease must exist and belong to the task.

3. Review gate behavior:
   - Return JSON only.
   - `decision` must be one of `approved`, `changes_requested`, `blocked`.
   - Record safe bounded metadata only: worker_id, task_id, lease_id, decision, reviewer, summary_present/summary_preview, checks_passed, patch_exported, created_at.
   - Do not record raw patch, raw diff, raw task goal, steps, prompts, env vars, shell output, request strings, secrets, or full reviewer notes.
   - Store the review gate as an auditable durable event or durable artifact using existing local patterns.
   - `get_worker_workspace_review_gate` should return the latest gate for that worker/task, or a bounded no-gate result.
   - Event/store failure must return a bounded JSON error and must not mutate worker/task/lease state.

4. Compatibility:
   - Preserve existing behavior of workspace lease tools, file inspection tools, write tools, change summary/patch export tools, sandbox guard tools, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` or the most appropriate existing durable-event test file covering:

- Approved gate records safe metadata and can be retrieved.
- `changes_requested` and `blocked` decisions are accepted.
- Unknown decision rejected.
- Unknown worker, no lease, task mismatch, offline/idle worker rejected.
- Output/event serialization does not leak raw task goal, steps, summary body, patch/diff, shell/env/request strings, or secret sentinels.
- `get_worker_workspace_review_gate` returns bounded no-gate result before any record exists.
- Recording a gate does not mutate project root, worker workspace, task/worker state, or lease ownership.
- Existing change summary/patch export/read/list/write/preview tools still work after recording a gate.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared durable event helpers broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
