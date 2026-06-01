# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-046: Context compiler v2 — structured memory recall.

Nora's automatic context now recalls structured memory. Bring the same capability into the explicit `compile_context_pack` developer tool so workers can request a richer, bounded context pack that includes relevant structured project knowledge.

## Scope

Keep this as a focused context-compiler slice. Do not add model routing, worker automation, sandboxing, UI changes, background memory writing, or durable-event summarization in this task.

1. Extend `ContextCompiler`:
   - Add an optional `MemoryRecordStore` dependency.
   - Add compile options for structured memory recall, for example:
     - `include_memory_records: bool = True`
     - `memory_query: Optional[str] = None`
     - `memory_max_results: int = 3`
   - Search records using `memory_query` or `task_description`.
   - Add a distinct `Structured Memory` / `结构化记忆` section to the compiled context pack.

2. Safety and bounding:
   - Reuse or extract the same safety rules used by `ContextSystem` structured-memory recall.
   - Do not include records with unsafe title/content/tags/source/related_task_id.
   - Bound per-record content and total section output.
   - Preserve existing `max_chars` pack budget behavior.

3. Tool wiring:
   - Wire `MemoryRecordStore` into the `ContextCompiler` instance built by `build_default_registry()`.
   - Ensure the `compile_context_pack` tool exposes the new options through its schema.
   - Existing calls without new args must remain compatible.

4. Tests:
   - Add focused tests in `tests/test_context_compiler.py`.
   - Cover memory record recall by default query.
   - Cover explicit `memory_query`.
   - Cover disabling memory recall.
   - Cover unsafe record omission, metadata safety, max result bounding, and compatibility with existing git/file/RAG sections.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_context_compiler tests.test_context_memory tests.test_memory_records tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch registry builder wiring broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
