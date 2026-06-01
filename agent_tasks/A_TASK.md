# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-042: Review memory capture v1.

Nora now has structured local memory records. Add a narrow, explicit capture layer that turns bounded review/task summaries into structured memory records, so approved work can become durable project knowledge without saving raw diffs, prompts, shell output, or full DONE/REVIEW files.

## Scope

Build the smallest safe runtime slice. Do not add LLM summarization, automatic transcript ingestion, filesystem watchers, or background automation in this task.

1. Add a review-memory capture module:
   - Suggested module: `mini_agent/review_memory.py`.
   - Provide a function/class that can create one or more `MemoryRecordStore` records from explicit fields:
     - `task_id`
     - `status` (`approved`, `changes_requested`, `blocked`)
     - `title`
     - `summary`
     - `learnings`
     - `risks`
     - `decisions`
     - `source`
   - For `approved`, allow writing bounded `task_learning`, `decision`, `risk`, and/or `fact` records.
   - For `changes_requested` or `blocked`, do not write durable `decision`/`fact` records by default. At most write a bounded `risk` record if an explicit risk is provided.

2. Safety and dedupe:
   - Reject or skip secret-like content using existing sensitivity checks.
   - Never save raw diff markers, shell command output, env vars, prompts, complete DONE/REVIEW bodies, or file contents.
   - Bound title/content lengths.
   - Add deterministic dedupe so repeated capture for the same `task_id/status/title/kind` does not create duplicate records.
   - Use `related_task_id`, `source="review"` or equivalent, and useful tags such as `review`, `task`, `approved`.

3. Registry tool:
   - Add one explicit tool, e.g. `capture_review_memory`.
   - The tool accepts structured summary fields, not raw files.
   - It returns bounded JSON listing created/skipped records.
   - It should use the existing `registry.memory_record_store` wiring.

4. Documentation:
   - Update `docs/knowledge/MEMORY_KERNEL.md` or add a short doc section explaining review-memory capture and safety boundaries.

## Suggested Tests

Add focused tests, likely `tests/test_review_memory.py`:

1. Approved review creates expected `task_learning` / `decision` / `risk` records.
2. Changes requested does not create `decision` or `fact` records.
3. Explicit risk on changes requested can create a bounded `risk`.
4. Dedupe prevents repeated capture duplicates.
5. Secret-like content is rejected/skipped.
6. Raw diff/shell/env/prompt-like content is rejected/skipped.
7. Registry tool returns bounded JSON and does not expose full content except record IDs/titles/kinds.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_review_memory tests.test_memory_records tests.test_mini_agent tests.test_tool_cache
python3 evals/run_evals.py
git diff --check
```

If you touch registry builder broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
