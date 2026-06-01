# Claude B Completion Report

Task: TASK-055 — Deterministic eval coverage for durable recovery plans
Status: ready for Codex review

## Summary

Added 4 deterministic offline eval cases for durable recovery plans (TASK-054 runtime). Applied PM review fixes.

## Review Fixes

1. **next_step_id assertion tightened** — After marking step 1 done, the latest checkpoint targets step 2 (still pending). Changed from `next_step_id in (1, 2)` to strict `next_step_id == 2` with explanatory comment.

2. **safety eval strengthened with direct state injection** — Now injects sentinels into task state via `get_task()` + `upsert_task()`:
   - `step.note` with sentinel
   - `step.summary` with sentinel
   - `checkpoint.description` with sentinel
   - `checkpoint.state_snapshot` with nested sentinel + secret-like `api_token` key
   - Asserts all sentinels and secret-like values absent from plan output

## Eval Cases

- **recovery_plan_basics** — Checkpoint selection, resume_policy, next_step_id (strict == 2), counts, can_resume, bounded JSON.
- **recovery_plan_selection_fallback** — Explicit checkpoint_id, step_id, missing step fallback, no-checkpoint, unknown task/checkpoint, bad step_id, terminal status.
- **recovery_plan_safety** — Injected sentinel goal/step/note/summary/desc/state_snapshot/api_token all absent from output. Allowed-fields-only check.
- **recovery_plan_compatibility** — Task state unchanged after planning. Error plans don't break existing tools.

## Diff

```text
 evals/run_evals.py | 218 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 218 insertions(+)
```

## Tests

```text
python3 evals/run_evals.py
198 passed, 0 failed

python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 452 tests in 6.947s — OK

git diff --check evals/run_evals.py
OK
```

## Notes

- No runtime code changed.
- No commit or push performed.
- Known issues: none.
