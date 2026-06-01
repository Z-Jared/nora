# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-044: Structured memory recall in Nora auto-context v1.

Nora now has structured local memory records and explicit review-memory capture. Add the first runtime recall slice so relevant structured records can appear in Nora's automatic context pack for future turns.

## Scope

Build a narrow, safe recall path. Do not add LLM summarization, background workers, file watchers, model routing, or automatic memory writing in this task.

1. Extend `ContextSystem` to support structured memory records:
   - Add an optional `MemoryRecordStore` dependency.
   - Search structured records using the user query/task text.
   - Add a distinct context section, e.g. `结构化记忆`, before or near existing long-term memory.
   - Include bounded, useful fields only: kind, title, concise content, tags/source/task id if useful.
   - Bound per-record and total structured-memory output.

2. Safety:
   - Never include records whose title/content/tags/source look sensitive via existing sensitivity checks.
   - Treat recalled memory as untrusted reference material, consistent with the current context-pack warning.
   - Do not include raw prompts, diffs, shell output, env vars, full DONE/REVIEW files, or huge content.
   - Keep normal technical records useful, e.g. decisions and task learnings should remain readable.

3. Wiring:
   - Wire structured memory recall into the app path that builds `ContextSystem`.
   - Avoid creating a second unrelated store when an existing DB-backed `MemoryRecordStore` can be used.
   - Keep existing long-term memory, context summary, and project RAG behavior compatible.

4. Tests:
   - Add focused tests, likely in `tests/test_context_memory.py` or `tests/test_context_system.py`.
   - Cover relevant structured record recall by query.
   - Cover no section when no records match.
   - Cover bounding and sensitive record filtering.
   - Cover coexistence with existing long-term memory/context summaries.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_context_memory tests.test_context_compiler tests.test_memory_records tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch app wiring broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
