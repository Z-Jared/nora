# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-039: eval coverage for native memory record store.

Add deterministic offline eval coverage for TASK-038 structured memory records. The evals should prove the feature is local-first, bounded, safe, and does not break existing memory tools.

## Scope

Edit `evals/run_evals.py` only unless you discover a real runtime bug. If TASK-038 is not present yet, wait or write `agent_tasks/B_DONE.md` as blocked by missing runtime.

Do not call external APIs.

Add eval cases covering:

1. Memory record basics:
   - Save decision/preference/fact records.
   - Search by query/tags/scope.
   - List returns bounded summaries.
   - Get returns the full selected record.
   - Delete removes the record.

2. Safety:
   - Secret-like content is rejected or redacted according to TASK-038 behavior.
   - List/search summaries do not leak oversized content.
   - No env vars, prompts, shell output, diffs, or unrelated event payloads appear in outputs.

3. Compatibility:
   - Legacy `save_memory`/`search_memory` still work.
   - Supermemory tools still remain optional/no-key safe.

4. Failure isolation:
   - Broken/invalid input returns JSON errors, not crashes.

Keep evals offline and deterministic.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_memory_records tests.test_mini_agent tests.test_tool_cache
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
