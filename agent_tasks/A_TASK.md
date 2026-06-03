# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-080: Worker workspace merge finalization v1.

TASK-076 reviewed merge apply and TASK-078 merge apply audit/history are approved. TASK-079 audit eval coverage is running in parallel with Claude B. Start implementation now.

Nora can now apply reviewed worker workspace changes and audit those apply events. The next step is a guarded finalization tool that lets Codex PM close out the durable task/worker/lease after a successful apply.

Do not implement project-root writes, git commits, git pushes, shell execution, process isolation, Docker, UI changes, model routing, worker auto-start, or deletion of workspace directories in this task.

## Scope

1. Add a registry-level finalization tool near the worker workspace apply/audit section in `mini_agent/toolkits/registry_builder.py`.

   Suggested tool name:
   - `finalize_worker_workspace_merge(worker_id, task_id, release_workspace=True)`

2. Gate finalization strictly:
   - Reuse existing worker/task/workspace lease validation.
   - Require at least one successful `workspace_merge_apply` audit event for the worker/task/lease.
   - If no successful apply event exists, return bounded JSON with `finalized: false` and safe reason label.
   - Do not trust caller-provided apply metadata.

3. Finalization behavior:
   - Mark the durable task completed using existing lifecycle/store patterns.
   - Mark the worker idle and clear current_task_id.
   - If `release_workspace` is true, release the active workspace lease using existing release behavior.
   - Do not delete workspace directories.
   - Do not write project root files.
   - Do not apply patches.
   - Keep operation idempotent where possible: repeated finalization after completion should return bounded already-finalized metadata rather than corrupting state.

4. Output:
   - Return JSON only.
   - Return bounded safe metadata:
     - finalized boolean
     - worker_id, task_id, lease_id
     - task_status_before/after
     - worker_status_before/after
     - workspace_released boolean
     - safe reason labels / error labels
   - Avoid raw file content, raw patch text, summary body, task goal, steps, prompts, env vars, shell output, request strings, reviewer notes, raw exception strings, or secrets.

5. Event/audit:
   - Record a safe durable event for successful finalization if an established event pattern is available.
   - Event payload must contain only safe metadata.
   - Event-store failure must not corrupt finalized task/worker/lease state; follow existing best-effort patterns.

6. Compatibility:
   - Preserve existing apply, audit, dry-run, summary, patch export, review gate, workspace lease, sandbox guard, read/list/preview/write, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.
   - Since B is running TASK-079 in parallel, do not edit `evals/run_evals.py` in this task.
   - If you discover a TASK-078 runtime bug that blocks this task, stop and write it in `agent_tasks/A_DONE.md`; do not broad-refactor.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` covering:

- Finalizes after successful apply event: task completed, worker idle/current_task cleared, lease released when requested.
- Rejects finalization before apply.
- `release_workspace=false` keeps lease while still completing task/worker.
- Repeated finalization is bounded/idempotent.
- Unknown worker, no lease when release required, task mismatch, offline/idle edge cases, and invalid `release_workspace` handling if applicable.
- Output and event payload do not leak raw file content, patch text, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
- Does not mutate project root or worker workspace contents.
- Existing apply/audit/dry-run/summary/patch/review gate/read/list/write/preview/claim/dispatch tools still behave after finalization where applicable.

## Verification

Run at minimum:

```bash
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
