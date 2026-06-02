# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-076: Worker workspace reviewed merge apply v1.

TASK-074 dry-run runtime and TASK-075 deterministic eval coverage are approved. Start implementation now.

Nora can now safely determine whether a worker workspace is ready for a reviewed merge. The next step is a guarded apply tool that copies approved worker workspace changes into the project root. This task writes project files, so it must be conservative and rollback-capable.

Do not implement git commits, git pushes, shell execution, process isolation, Docker, UI changes, model routing, worker auto-start, or deletion semantics in this task.

## Scope

1. Add a registry-level reviewed merge apply tool near the existing worker workspace change export / review gate / dry-run section in `mini_agent/toolkits/registry_builder.py`.

   Suggested tool name:
   - `apply_reviewed_worker_workspace_merge(worker_id, task_id, max_files=50)`

2. Gate apply strictly:
   - Reuse existing worker/task/workspace lease validation.
   - Re-run `dry_run_worker_workspace_merge` at apply time.
   - If dry-run is not `ready: true`, return bounded JSON with `applied: false` and safe reason labels.
   - Do not trust stale caller-supplied preflight output.

3. Apply behavior:
   - Write only created/modified safe text files identified by current summary/patch export safety rules.
   - Re-check every project-root target path immediately before write.
   - Reject/skips must block the whole apply.
   - Do not apply raw patches.
   - Do not delete files.
   - Do not write symlink targets, binary files, oversized files, denied paths, path escapes, or project symlink-to-sensitive/escape paths.
   - If any file write fails after earlier writes, rollback:
     - restore modified files from pre-apply content
     - remove files created by this apply
   - On rollback failure, return bounded JSON with rollback failure metadata only; never leak file contents.

4. Output:
   - Return JSON only.
   - Return bounded safe metadata:
     - `applied` boolean
     - worker_id, task_id, lease_id
     - created/modified/applied counts
     - bounded list of safe file paths and statuses
     - safe reason labels / error labels
   - Avoid raw file content, raw patch text, summary body, task goal, steps, prompts, env vars, shell output, request strings, reviewer notes, or secrets.

5. Event/audit:
   - Record a safe durable event for successful apply if there is an established event pattern available.
   - Event payload must contain only safe metadata: worker/task/lease ids, counts, path/status metadata, and no content.
   - Event-store failure must not corrupt already-applied files; return bounded behavior consistent with existing registry patterns.

6. Compatibility:
   - Preserve existing behavior of dry-run, workspace lease tools, file inspection tools, write tools, change summary/patch export tools, review gate tools, sandbox guard tools, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` covering:

- Applies created and modified safe text files after approved ready dry-run.
- Rejects no gate, changes_requested, blocked, no changes, skipped summary/patch entries, and patch budget overflow.
- Rejects unknown worker, no lease, task mismatch, offline/idle worker, and bad `max_files`.
- Blocks sensitive path, binary, oversized, symlink escape, and project symlink-to-sensitive-file cases.
- Does not leak raw patch, raw file content, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
- Rollback restores modified files and removes newly created files if a later write fails.
- Successful apply mutates only intended project files; worker workspace, worker/task state, lease ownership, and review gate remain unchanged.
- Existing dry-run/summary/patch/review gate/read/list/write/preview/claim/dispatch tools still work after apply.

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
