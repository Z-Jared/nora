# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-074: Worker workspace reviewed merge dry-run v1.

TASK-072 runtime and TASK-073 deterministic eval coverage are approved and pushed. Start implementation now.

Nora can now export worker workspace summaries/patches and record review gate decisions. The next step is a safe dry-run preflight that tells Codex PM whether a worker workspace output is ready for a future merge workflow. This task must remain read-only.

Do not implement project-root merge, patch apply to project root, git worktrees, shell execution, process isolation, Docker, UI changes, or model routing in this task.

## Scope

1. Add a minimal registry-level dry-run tool near the existing worker workspace change export / review gate section in `mini_agent/toolkits/registry_builder.py`.

   Suggested tool name:
   - `dry_run_worker_workspace_merge(worker_id, task_id, max_files=50)`

2. Reuse existing worker workspace validation:
   - Worker must exist.
   - Worker must not be offline or idle.
   - `worker.current_task_id == task_id`.
   - Task must exist.
   - `task.worker_id == worker_id`.
   - Active lease must exist and belong to the task.

3. Dry-run behavior:
   - Return JSON only.
   - Do not write to project root or worker workspace.
   - Do not apply patches.
   - Do not mutate task/worker/lease state.
   - Inspect current worker workspace change summary and patch export behavior using the same safety rules as TASK-070.
   - Inspect latest worker workspace review gate using TASK-072 behavior.
   - Return bounded safe metadata:
     - worker_id, task_id, lease_id
     - `ready` boolean
     - `decision` / `has_review_gate`
     - `requires_review` boolean
     - counts for created/modified/same/skipped files
     - patch count, skipped patch count, patch_bytes
     - safe reason labels explaining why not ready
   - `ready` should only be true when:
     - latest review gate exists and decision is `approved`
     - summary has at least one created/modified file or patch export has at least one patch
     - patch export has no skipped entries
     - summary has no skipped entries
     - patch_bytes is within existing budget
   - If latest gate is `changes_requested` or `blocked`, return `ready: false` with reason label.
   - If no gate exists, return `ready: false`, `requires_review: true`.
   - Avoid raw file content, raw patch text, raw summary body, task goal, steps, prompts, env vars, shell output, request strings, secrets, or full reviewer notes.
   - Event/store failure or internal helper failure must return bounded JSON errors without leaking raw exception strings.

4. Compatibility:
   - Preserve existing behavior of workspace lease tools, file inspection tools, write tools, change summary/patch export tools, review gate tools, sandbox guard tools, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` covering:

- Ready when there is an approved gate and safe created/modified patchable changes.
- Not ready when no review gate exists (`requires_review: true`).
- Not ready for `changes_requested` and `blocked`.
- Not ready for no changes.
- Not ready when summary or patch export has skipped entries (sensitive path, binary, oversized, project symlink-to-sensitive-file, patch budget).
- Unknown worker, no lease, task mismatch, offline/idle worker rejected.
- Output does not leak raw patch, raw file content, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
- Dry-run does not mutate project root, worker workspace, task/worker state, or lease ownership.
- Existing summary/patch export/review gate/read/list/write/preview tools still work after dry-run.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
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
