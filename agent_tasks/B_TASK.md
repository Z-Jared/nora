# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-047: Deterministic eval coverage for Context compiler structured memory recall.

Add offline eval coverage for TASK-046 so `compile_context_pack` can safely include structured memory records without leaking unsafe records or breaking existing context compiler behavior.

## Scope

Edit `evals/run_evals.py` only unless you discover a real TASK-046 runtime bug. If TASK-046 runtime is not present yet, wait or write `agent_tasks/B_DONE.md` as blocked by missing runtime.

Do not call external APIs.

Add deterministic eval cases covering:

1. Recall basics:
   - Save structured memory records.
   - Call the real `compile_context_pack` registry tool.
   - Matching records appear in the structured memory section with kind/title/bounded content.

2. Query controls:
   - Default query uses task description.
   - Explicit `memory_query` can recall a record not matched by the task description.
   - `include_memory_records=false` suppresses the memory section.

3. Safety:
   - Unsafe content and unsafe metadata records are omitted.
   - Prompt/diff/shell/env-like records do not appear.
   - Oversized record content is bounded and does not leak raw full content.

4. Compatibility:
   - Existing git status / changed files / file outline / RAG sections still work.
   - Existing context compiler evals continue passing.
   - Pack budget behavior remains deterministic when memory records are large.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_context_compiler tests.test_context_memory tests.test_memory_records tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
