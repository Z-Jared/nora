# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-054: Durable recovery plan tool v1.

Nora now has durable lifecycle controls and explicit checkpoint creation. The next narrow step toward replay/recovery is a read-only registry tool that can inspect durable task state and checkpoints and return a safe recovery plan for where a future agent should resume. This task must not execute recovery, start workers, run model calls, edit files, or mutate task state.

## Scope

Build only recovery plan inspection. Do not implement replay execution, worker process execution, worktree creation, patch queues, broad schema redesign, or automatic task mutation.

1. Add a read-only registry tool:
   - Suggested name: `plan_durable_recovery(task_id, checkpoint_id="", step_id="")`
   - Register near existing durable task registry tools in `mini_agent/toolkits/registry_builder.py`.
   - Unknown task ids should return JSON `{"error": ...}`.
   - Unknown checkpoint ids should return JSON `{"error": ...}`.
   - Non-integer `step_id` should return JSON `{"error": ...}` without crashing.
   - This tool should have read-only task permission/risk.

2. Recovery plan semantics:
   - If `checkpoint_id` is provided, select exactly that checkpoint.
   - Else if `step_id` is provided, select the latest checkpoint for that step when one exists.
   - Else select the latest checkpoint when any checkpoint exists.
   - If no checkpoint exists, still return a plan with `selected_checkpoint_id` empty/null and a `resume_policy` of `from_step` or `from_beginning`.
   - Compute a bounded `next_step_id`:
     - Prefer the selected checkpoint's step id when that step is not done/skipped.
     - Otherwise choose the first step that is not done/skipped.
     - If all steps are done/skipped, use `current_step` when present, otherwise empty/null.
   - Set `can_resume` false for completed/cancelled tasks; true for pending/running/paused/blocked/failed tasks.
   - Include safe reason labels such as `checkpoint_selected`, `step_checkpoint_missing`, `no_checkpoint`, `terminal_status`, or `all_steps_done`.

3. Bounded output:
   - Return only safe metadata:
     - `task_id`
     - `status`
     - `can_resume`
     - `resume_policy`
     - `selected_checkpoint_id`
     - `checkpoint_step_id`
     - `next_step_id`
     - `checkpoint_count`
     - `step_count`
     - `incomplete_step_count`
     - `trace_ref_count`
     - `worker_id_present`
     - `reason`
   - Do not return raw task goal, raw step text, notes, summaries, checkpoint descriptions, raw `state_snapshot`, prompts, diffs, shell output, env vars, full tool outputs, or secret-like values.

4. Compatibility:
   - Do not mutate durable task state.
   - Preserve existing behavior of `get_durable_task`, `list_durable_tasks`, lifecycle controls, and checkpoint creation.
   - Support both SQLite-backed store and JSONL-backed store if your implementation touches store-level helpers.

5. Tests:
   - Add focused tests in `tests/test_durable_tasks.py`.
   - Cover latest checkpoint selection.
   - Cover explicit `checkpoint_id` selection.
   - Cover `step_id` selection and missing step checkpoint behavior.
   - Cover no-checkpoint fallback.
   - Cover completed/cancelled `can_resume=false`.
   - Cover unknown task, unknown checkpoint, and non-integer `step_id`.
   - Cover safe output and no raw goal/step/note/summary/checkpoint description/state snapshot/secret leakage.
   - Cover no mutation of task state.
   - Cover JSONL backend only if you add store-level helper behavior.

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
