# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-045: Deterministic eval coverage for structured memory recall.

Add offline eval coverage for TASK-044 so Nora's automatic context pack can safely recall relevant structured memory records without leaking unsafe content or breaking existing context sources.

## Scope

Edit `evals/run_evals.py` only unless you discover a real TASK-044 runtime bug. If TASK-044 runtime is not present yet, wait or write `agent_tasks/B_DONE.md` as blocked by missing runtime.

Do not call external APIs.

Add deterministic eval cases covering:

1. Recall basics:
   - Save structured memory records through the existing store/tool path.
   - Build the app/context path or `ContextSystem` path used by runtime.
   - `context_pack(query)` includes relevant structured memory title/content for matching queries.

2. Ranking/filtering behavior:
   - Irrelevant records do not appear for unrelated queries.
   - Multiple matching records are bounded by max results/char limits.
   - Kinds such as `decision`, `task_learning`, and `risk` are formatted clearly enough to be useful.

3. Safety:
   - Secret-like record title/content is omitted.
   - Prompt/diff/shell/env-like content does not appear in context output if present in stored records.
   - Context output does not expose oversized raw content.

4. Compatibility:
   - Existing context summaries, long-term memory, and project snippets still work.
   - Empty/no-match structured memory does not suppress other context sections.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_context_memory tests.test_context_compiler tests.test_memory_records tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
