# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-056: Durable recovery plan event logging v1.

Nora now has a read-only `plan_durable_recovery` tool and deterministic eval coverage. The next small step toward replayable recovery is to make recovery planning itself auditable by recording a bounded durable event whenever a recovery plan is generated.

## Scope

Build only event logging for recovery planning. Do not implement replay execution, worker process execution, worktree creation, patch queues, broad schema redesign, or automatic task mutation.

1. Add a durable event type:
   - Suggested constant: `RECOVERY_PLANNED = "recovery_planned"` in `mini_agent/durable_events.py`.
   - Ensure it can be stored and queried like other durable events without schema migration beyond existing event fields.

2. Record a safe event from `plan_durable_recovery`:
   - Event type: `RECOVERY_PLANNED`.
   - `task_id`: task id.
   - `checkpoint_id`: selected checkpoint id when present, otherwise empty/null.
   - `source`: `registry`.
   - `severity`: `info`.
   - `summary`: short generic string such as `recovery planned`.
   - Payload should include only safe metadata:
     - `operation="plan_recovery"`
     - `can_resume`
     - `resume_policy`
     - `reason`
     - `selected_checkpoint_present`
     - `checkpoint_step_id`
     - `next_step_id`
     - `checkpoint_count`
     - `step_count`
     - `incomplete_step_count`
     - `trace_ref_count`
     - `worker_id_present`
     - `requested_checkpoint_id_present`
     - `requested_step_id_present`

3. Safety and behavior:
   - Do not record raw task goal, raw step text, notes, summaries, checkpoint descriptions, raw `state_snapshot`, prompts, diffs, shell output, env vars, full tool outputs, checkpoint request strings, or secret-like values.
   - Event logging failure must not prevent `plan_durable_recovery` from returning its plan.
   - Error responses for unknown task/checkpoint/bad step_id may skip event logging unless there is already a safe local pattern for error events; do not add risky logging for invalid raw input.
   - The tool may remain `risk="read"`; the event log side-effect is audit metadata only.

4. Compatibility:
   - Do not mutate durable task state.
   - Preserve existing behavior of `get_durable_task`, `list_durable_tasks`, lifecycle controls, and checkpoint creation.
   - Preserve all TASK-054/TASK-055 tests.

5. Tests:
   - Add focused tests in `tests/test_durable_tasks.py` and/or `tests/test_durable_events.py`.
   - Cover successful `RECOVERY_PLANNED` event for selected checkpoint.
   - Cover no-checkpoint fallback event.
   - Cover top-level `checkpoint_id` linkage when a checkpoint is selected.
   - Cover payload contains only safe metadata and no raw goal/step/note/summary/checkpoint description/state_snapshot/secret sentinel.
   - Cover event-store failure isolation.
   - Cover `plan_durable_recovery` still does not mutate task state.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you touch shared registry builder paths broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
