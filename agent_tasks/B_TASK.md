# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-043: Deterministic eval coverage for review memory capture.

Add offline eval coverage for TASK-042 so review/task summaries can safely become structured local memory records without leaking raw artifacts or creating duplicates.

## Scope

Edit `evals/run_evals.py` only unless you discover a real TASK-042 runtime bug. If TASK-042 runtime is not present yet, wait or write `agent_tasks/B_DONE.md` as blocked by missing runtime.

Do not call external APIs.

Add eval cases covering:

1. Approved capture:
   - `capture_review_memory` creates task learning and decision/risk records from explicit bounded fields.
   - Created records are searchable via `search_memory_records`.

2. Non-approved statuses:
   - `changes_requested` and `blocked` do not create durable decision/fact records.
   - Explicit risk can create a risk record.

3. Safety:
   - Secret-like content is rejected/skipped.
   - Raw diff markers, shell output, env var names, prompts, and oversized content do not appear in memory search/list outputs.
   - Tool output is bounded and does not include raw full content.

4. Dedupe:
   - Repeating the same capture for `task_id/status/title/kind` does not create duplicate records.

5. Failure isolation:
   - Invalid status, empty title/summary, malformed inputs, or missing optional fields return JSON errors/skips, not crashes.
   - Existing memory record tools still work after capture errors.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_review_memory tests.test_memory_records tests.test_mini_agent tests.test_tool_cache
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
