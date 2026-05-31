# Claude B Completion Report - TASK-035

Status: completed, ready for Codex review

## Summary

Added deterministic offline eval coverage for durable worker heartbeat/offline lifecycle (TASK-032).

Five new eval cases added to `evals/run_evals.py`:

1. **worker_heartbeat_basics** — `touch_worker` updates `last_seen_at` for existing worker. Unknown, empty, and whitespace worker IDs return JSON errors.

2. **worker_offline_lifecycle** — Stale worker is marked offline. Fresh worker is not. Already-offline worker is not counted as newly changed. Marking offline preserves `current_task_id`.

3. **worker_offline_task_isolation** — Marking worker offline does not mutate durable task ownership (`worker_id`) or task status.

4. **worker_heartbeat_safety** — Sentinel role/path/goal/secret values injected. Asserts sentinels absent from touch output, offline output, and serialized events.

5. **worker_heartbeat_failure_isolation** — Broken event store must not change `touch_worker` or `mark_stale_workers_offline` behavior.

## Safety Assertions

- Sentinel strings used for: worker role, workspace path, task goal, and a secret-like token
- All sentinels verified absent from: touch output, offline output, and serialized durable events

## Diff

```text
 evals/run_evals.py | 217 ++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 217 insertions(+)
```

## Tests

```text
python3 evals/run_evals.py
152 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_durable_tasks tests.test_mini_agent
Ran 441 tests in 8.218s
OK

git diff --check
(clean)
```

## Notes

- No runtime code changed — eval only as instructed.
- TASK-032 implementation was already complete and approved.
- No commit or push performed.
- Known limitations: none.
