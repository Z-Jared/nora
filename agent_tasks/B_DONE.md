# Claude B Completion Report

Task: TASK-057 — Deterministic eval coverage for recovery-plan events
Status: ready for Codex review

## Summary

Added 4 deterministic offline eval cases for recovery-plan events (TASK-056 runtime).

- **recovery_event_basics** — `RECOVERY_PLANNED` event recorded with `checkpoint_id` top-level linkage (matches selected checkpoint), `source=registry`, `severity=info`, and safe payload fields (operation, can_resume, resume_policy, reason, counts, presence flags). Bounded payload (no goal/steps/description/state_snapshot/notes).

- **recovery_event_selection_fallback** — Events for: explicit `checkpoint_id` selection (linkage + `requested_checkpoint_id_present=True`), `step_id` selection (`requested_step_id_present=True`), no-checkpoint fallback (`checkpoint_id=""`, `reason=no_checkpoint`), terminal status (`can_resume=False`, `reason=terminal_status`).

- **recovery_event_safety** — Injects sentinels into step.note/summary, checkpoint.description/state_snapshot (nested + secret-like api_token). All sentinels and secret-like values absent from `event.to_dict()` serialized output. Allowed-fields-only check on payload keys.

- **recovery_event_compatibility** — Broken event store doesn't prevent planning. Task state (status, steps, checkpoints) unchanged after planning. Existing tools (get_durable_task, list_durable_tasks, update_durable_task) still work.

## Diff

```text
 evals/run_evals.py | 204 +++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 203 insertions(+), 1 deletion(-)
```

## Tests

```text
python3 evals/run_evals.py
202 passed, 0 failed

python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 458 tests in 7.655s — OK

git diff --check evals/run_evals.py
OK
```

## Notes

- No runtime code changed (TASK-056 was already complete).
- No commit or push performed.
- Eval count increased from 198 to 202.
- Known issues: none.
