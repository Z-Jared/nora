# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-037: eval coverage for optional Supermemory memory toolkit.

Add deterministic offline eval coverage for the Supermemory integration from TASK-036. The evals must prove the integration is optional, safe, bounded, and failure-isolated.

## Scope

Edit `evals/run_evals.py` only unless you discover a real runtime bug. If TASK-036 is not present yet, wait or write `agent_tasks/B_DONE.md` as blocked by missing runtime.

Do not call the real Supermemory API. Use monkeypatch/fake client/fake HTTP behavior as appropriate for the implementation.

Add eval cases covering:

1. Optional configuration:
   - With no `SUPERMEMORY_API_KEY`, Nora still starts and existing evals remain offline.
   - Supermemory tools either are absent or return a clear JSON configuration error, matching TASK-036 behavior.

2. Save behavior:
   - `supermemory_save` stores only explicit content and namespace/container metadata.
   - It must not include env vars, raw prompts, shell output, diffs, or unrelated task/event payloads.

3. Search/profile behavior:
   - Search/profile output is bounded.
   - Large fake API payloads are truncated or summarized.
   - Secret-like sentinel values are not leaked in returned summaries unless they are the explicit searched/saved content and the implementation intentionally returns them.

4. Failure isolation:
   - Network/API error returns JSON error and does not crash registry calls.
   - Existing memory tools still work without Supermemory configured.

Keep evals offline and deterministic.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_mini_agent tests.test_tool_cache
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
