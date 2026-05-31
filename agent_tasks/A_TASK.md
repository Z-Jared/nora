# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-038: Nora native memory record store v1.

Supermemory is now optional external memory. Add Nora's own local-first structured memory record store so durable decisions, preferences, task learnings, and project facts can be saved as typed records instead of plain long-term memory text.

## Scope

Implement a narrow local memory-kernel slice. Do not add embeddings, graph traversal, reflection automation, or automatic transcript ingestion in this task.

1. Add a structured memory record model/store:
   - Suggested module: `mini_agent/memory_records.py`.
   - `MemoryRecord` fields should include at least:
     - `record_id`
     - `kind` (`decision`, `preference`, `fact`, `task_learning`, `risk`, `note`)
     - `scope` (project/user/global string)
     - `title`
     - `content`
     - `tags`
     - `source`
     - `confidence`
     - `related_task_id`
     - `created_at`
     - `updated_at`
   - Support SQLite via `NoraDB` and JSONL fallback.
   - Provide store methods: create, get, list, search, delete.

2. Registry tools:
   - `save_memory_record`
   - `search_memory_records`
   - `list_memory_records`
   - `get_memory_record`
   - `delete_memory_record`
   - Keep outputs bounded JSON.

3. Safety:
   - Do not automatically save prompts, diffs, shell output, traces, files, or env vars.
   - Reject or redact obvious secret-like content.
   - Search/list outputs should return summaries; full content only from get.
   - Existing `save_memory`/`search_memory` tools must keep working unchanged.

4. Documentation:
   - Add a short `docs/knowledge/MEMORY_KERNEL.md` explaining the role of structured local records and how they differ from Supermemory and legacy long-term memory.

## Suggested Tests

Add focused tests, likely `tests/test_memory_records.py`:

1. SQLite create/get/list/search/delete.
2. JSONL create/get/list/search/delete.
3. Registry tools return bounded JSON and validate kind/scope/title/content.
4. Secret-like content is rejected or redacted.
5. Existing long-term memory tools still work.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_memory_records tests.test_mini_agent tests.test_tool_cache
python3 evals/run_evals.py
git diff --check
```

If you touch database migrations or broad registry wiring, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
