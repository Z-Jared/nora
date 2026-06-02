# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-078: Worker workspace merge apply audit/history v1.

TASK-076 runtime is approved and TASK-077 eval coverage is running in parallel with Claude B. Start implementation now.

Nora can now apply reviewed worker workspace changes to the project root. The next step is a read-only audit/history surface so Codex PM can inspect prior workspace merge apply events without reading raw file content or patch text.

Do not implement new apply behavior, git commits, git pushes, shell execution, process isolation, Docker, UI changes, model routing, worker auto-start, or deletion semantics in this task.

## Scope

1. Add a read-only registry-level audit tool near the worker workspace merge apply section in `mini_agent/toolkits/registry_builder.py`.

   Suggested tool name:
   - `list_worker_workspace_merge_applies(worker_id="", task_id="", limit=20)`

2. Query behavior:
   - Read durable events for successful `apply_reviewed_worker_workspace_merge` operations.
   - Filter by optional `worker_id` and/or `task_id`.
   - Bound `limit` to 1..100 and reject non-integer input with bounded JSON error.
   - Return newest-first results consistent with existing durable event query behavior.
   - Return only events whose source/operation identify workspace merge apply.

3. Output:
   - Return JSON only.
   - Return bounded safe metadata:
     - count
     - event_id, created_at, worker_id, task_id, lease_id
     - applied_count, created_count, modified_count
     - bounded safe paths/status metadata if present
   - Avoid raw file content, raw patch text, summary body, task goal, steps, prompts, env vars, shell output, request strings, reviewer notes, raw exception strings, or secrets.
   - If event payloads are malformed or missing fields, return safe defaults rather than raw payload values.

4. Compatibility:
   - Preserve existing behavior of apply, dry-run, summary, patch export, review gate, workspace lease, sandbox guard, read/list/preview/write, claim/dispatch, durable task/worker/event tools, and project-level workspace tools.
   - Since B is running TASK-077 in parallel, do not edit `evals/run_evals.py` in this task.
   - If you discover a TASK-076 runtime bug that blocks this audit tool, stop and write it in `agent_tasks/A_DONE.md`; do not broad-refactor.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` covering:

- No merge apply events returns empty list.
- Successful apply creates an audit entry with safe counts and ids.
- Filtering by worker_id and task_id works.
- Limit bounds and bad limit handling.
- Malformed/unrelated file edit events are ignored or safely bounded.
- Output does not leak raw file content, patch text, task goal, steps, reviewer summary, shell/env/request strings, or secret sentinels.
- Audit tool is read-only and does not mutate project root, worker workspace, worker/task state, lease ownership, or review gate.
- Existing apply/dry-run/summary/patch/review gate/read/list/write/preview/claim/dispatch tools still work after audit query.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch durable event helpers broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
