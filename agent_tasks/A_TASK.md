# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-062: Worker workspace preparation integration.

Codex PM approved this task after review. TASK-060 workspace lease runtime and TASK-061 eval coverage are already integrated.

Nora can create durable worker workspace leases. The next runtime depth step is wiring workspace preparation into worker claim/dispatch flows so future worker execution has a workspace lease available before execution.

## Scope

Integrate workspace preparation into worker claim and dispatch. Do not implement sandbox policy, process isolation, git worktrees, patch queues, or real multi-process worker execution.

1. Claim integration:
   - `claim_durable_task(worker_id)` should best-effort prepare workspace after a successful claim.
   - Existing active assignment path should reuse existing workspace lease when possible.
   - Response should include bounded `workspace` metadata or a bounded `workspace.error`.
   - Workspace preparation failure must not block claim.

2. Dispatch integration:
   - `dispatch_durable_tasks(max_assignments=10)` should best-effort prepare workspace after each assignment.
   - Each assignment response should include bounded `workspace` metadata or bounded `workspace.error`.
   - Workspace preparation failure must not block dispatch.

3. Lease behavior:
   - Same worker + same task with existing lease should be idempotent and return `reused: true`.
   - Same task leased by a different worker must still return an error with `existing_lease_id`.
   - Worker with a lease for a different task must still return an error with `existing_lease_id`.

4. Safety and compatibility:
   - New workspace output must not leak raw task goal, steps, prompts, shell output, diffs, env vars, or secrets.
   - Preserve existing claim/dispatch task assignment behavior.
   - Preserve existing durable worker/task/event registry tools.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 -m unittest discover -s tests
python3 evals/run_evals.py
git diff --check
```

## Completion Report

Written in `agent_tasks/A_DONE.md`.

Do not commit or push.
