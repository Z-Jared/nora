# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-071: Deterministic eval coverage for worker workspace change export tools.

TASK-070 runtime is approved and visible in the worktree. Start implementation now.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-070 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, or browser sessions.

Planned deterministic offline eval coverage:

1. Change summary basics:
   - Prepare/claim a worker workspace.
   - `summarize_worker_workspace_changes` classifies created, modified, and same files.
   - Summary is bounded by `max_files`.
   - Summary returns metadata only and does not include raw file contents.

2. Patch export basics:
   - `export_worker_workspace_patch` exports created-file unified diff from `/dev/null`.
   - Modified files diff against the project-root version.
   - Same files are omitted from multi-file export.
   - Single-path same file returns a no-change result.
   - `context_lines` and `max_files` are bounded.

3. Sandbox and sensitive path safety:
   - Relative traversal and absolute path escape are rejected.
   - Unknown worker, no lease, task mismatch, offline worker, and idle worker are rejected.
   - Sensitive paths such as `.env`, `.env.local`, `.env.production`, `.git`, `logs`, `data`, `__pycache__`, and `.pytest_cache` are rejected or skipped.
   - Sensitive names used as intermediate path components are rejected or skipped.
   - Symlink escape and project-root symlink-to-sensitive-file do not leak target contents.

4. Bounded output and no mutation:
   - Binary/non-UTF8/oversized project or worker files return bounded errors/skips.
   - Single-file and multi-file patch output stay under the workspace byte budget.
   - Outputs do not leak task goal, steps, prompts, shell output, env vars, request strings, raw unrelated file content, or secret-like sentinels.
   - Error and success calls do not mutate project root, worker workspace, task/worker state, or lease ownership.

5. Compatibility:
   - Change export tools do not break worker/task registry tools, workspace lease tools, sandbox guard tools, file inspection tools, write tools, claim, or dispatch.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files and explain why in `agent_tasks/B_DONE.md`.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
