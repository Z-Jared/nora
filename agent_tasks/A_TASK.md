# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-052: Durable checkpoint control tools v1.

Nora already has durable checkpoints in `DurableTaskStore.add_checkpoint()` and TaskManager shadow sync, but there is no explicit registry tool for an agent or workflow to record a bounded checkpoint on demand. Add a narrow checkpoint control tool that creates safe, inspectable checkpoints without exposing raw prompts, diffs, shell output, or secrets.

## Scope

Build only explicit checkpoint creation. Do not implement replay/resume engine, worker process execution, worktree creation, or broad schema redesign in this task.

1. Add a registry tool:
   - Suggested name: `add_durable_checkpoint(task_id, step_id=0, description="", state_summary="")`
   - Register near existing durable task registry tools in `mini_agent/toolkits/registry_builder.py`.
   - Use existing `DurableTaskStore.add_checkpoint()`.
   - Unknown task ids should return JSON `{"error": ...}`.

2. Checkpoint semantics:
   - `step_id` should be parsed/bounded to an integer >= 0.
   - Store a bounded `state_snapshot` with safe metadata only, for example:
     - `task_status`
     - `current_step`
     - `step_id`
     - `description_present`
     - `state_summary_present`
   - Do not store raw task goal, raw step text, prompts, diffs, shell output, env vars, full tool outputs, or secret-like values.
   - Treat `description` and `state_summary` as presence metadata or bounded safe summaries only; if you include any text, bound it tightly and filter secret-like content.
   - Return bounded JSON summary: `task_id`, `checkpoint_id`, `step_id`, `checkpoint_count`, `description_present`, `state_summary_present`.

3. Step checkpoint ref:
   - If `step_id` matches an existing durable step, write the new checkpoint id into that step's `checkpoint_ref`.
   - Preserve existing checkpoints, trace refs, worker id, retry metadata, and task status.
   - Support both SQLite-backed store and JSONL-backed store.

4. Event logging and safety:
   - Record `CHECKPOINT_ADDED` event with safe metadata only: `operation="checkpoint"`, `checkpoint_id`, `step_id`, `checkpoint_count`, `description_present`, `state_summary_present`.
   - Include `checkpoint_id` top-level on the event where supported.
   - Event logging failures must not prevent checkpoint creation.

5. Tests:
   - Add focused tests in `tests/test_durable_tasks.py` and/or `tests/test_durable_events.py`.
   - Cover successful checkpoint creation via registry.
   - Cover step `checkpoint_ref` update when step exists.
   - Cover unknown task id and invalid/bounded `step_id`.
   - Cover safe output and no raw goal/step/summary/secret leakage.
   - Cover `CHECKPOINT_ADDED` event safe metadata and failure isolation.
   - Cover JSONL backend behavior if you add store-level helper behavior.

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
