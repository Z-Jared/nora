# Claude B Task

Owner: Claude B
Status: completed

## Goal

Implement TASK-014: eval coverage for durable file-edit event logging.

## Instructions

TASK-013 is complete in the main worktree and approved by reviewer. Add deterministic offline eval coverage for durable file-edit events in `evals/run_evals.py`.

Important: your isolated worktree may be stale and may still contain old TASK-012 eval changes. Do not reimplement TASK-013 runtime behavior. If your worktree does not contain `FILE_EDIT_STARTED`, `FILE_EDIT_FINISHED`, `FILE_EDIT_BLOCKED`, and `FILE_EDIT_ERROR`, stop and report the stale-worktree blocker in `agent_tasks/B_DONE.md` instead of inventing fallback imports or runtime shims.

Add eval cases for:

1. Successful file edit event:
   - Exercise a workspace write path.
   - Verify durable event log records started/finished events with safe file metadata.

2. Replace or patch metadata:
   - Exercise `replace`, `apply_unified_diff`, or `apply_multi_file_patch`.
   - Verify metadata includes paths/file counts/status without storing raw content, raw replacement text, full patch, or raw diff.

3. Blocked or cancelled edit:
   - Exercise sensitive path denial or confirmation cancellation.
   - Verify a blocked event is emitted and no finished event is incorrectly recorded.

4. Error or rollback behavior:
   - Exercise an edit failure path.
   - Verify an error event is emitted while preserving existing operation behavior.

5. Failure isolation:
   - Broken event store should not change existing workspace operation behavior.

6. Safety assertions:
   - Use sentinel strings that would fail the eval if raw content, raw patch/diff, or secret-like text is persisted in durable event payloads or serialized event records.

Keep evals offline and deterministic. Do not call live LLM APIs and do not reimplement TASK-013 runtime behavior in eval-only code.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_workspace tests.test_workspace_patch
```

## Context

- TASK-013 added `FILE_EDIT_STARTED`, `FILE_EDIT_FINISHED`, `FILE_EDIT_ERROR`, and `FILE_EDIT_BLOCKED`.
- `evals/run_evals.py` already has durable event lifecycle, tool-call event, and model-call event evals.
- Keep this task eval-only. Runtime changes belong to TASK-013 and should not be duplicated here.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
