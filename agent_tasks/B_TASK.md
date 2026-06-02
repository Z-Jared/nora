# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-073: Deterministic eval coverage for worker workspace review gate artifacts.

TASK-072 runtime is approved and visible in the worktree. Start implementation now.

## Scope

When assigned, edit `evals/run_evals.py` only unless you discover a real TASK-072 runtime bug.

Do not call external APIs. Do not start real agents, terminals, shell commands through Nora, or browser sessions.

Planned deterministic offline eval coverage:

1. Review gate basics:
   - Prepare/claim a worker workspace.
   - `record_worker_workspace_review_gate` records `approved`, `changes_requested`, and `blocked` decisions.
   - `get_worker_workspace_review_gate` returns `has_gate: false` before any record exists.
   - `get_worker_workspace_review_gate` returns the latest recorded gate after multiple decisions.

2. Validation and safety:
   - Unknown decision rejected.
   - Unknown worker, no lease, task mismatch, offline worker, and idle worker rejected.
   - Reviewer and summary inputs do not leak secrets, env-var-looking strings, raw patch/diff text, shell output, request strings, task goal, or steps.
   - Record/get error outputs are bounded and do not leak raw exception strings or secret sentinels.

3. Event and no-mutation behavior:
   - Review gate durable event payload contains safe metadata only.
   - Raw summary body, reviewer secret, task goal/steps, patch/diff, shell/env/request strings are not serialized in events.
   - Event-store failure returns bounded JSON error and does not mutate project root, worker workspace, worker/task state, or lease ownership.
   - Query failure returns bounded JSON error.

4. Compatibility:
   - Review gate tools do not break worker/task registry tools, workspace lease tools, sandbox guard tools, file inspection tools, write tools, change summary/patch export tools, claim, or dispatch.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files and explain why in `agent_tasks/B_DONE.md`.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
