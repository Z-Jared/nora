# Claude B Completion Report - TASK-049

Status: completed, ready for Codex review

## Summary

Added deterministic offline eval coverage for durable worker auto-dispatch (TASK-048).

Four new eval cases added to `evals/run_evals.py`:

1. **dispatch_basics** — Register 3 idle workers, create 3 pending tasks, dispatch with max_assignments=2. Proves oldest tasks dispatched first (t1, t2 dispatched; t3 not). Returns bounded JSON with dispatched count and assignment details.

2. **dispatch_limits_exclusions** — max_assignments=1 respected. ALL non-idle workers excluded (running, assigned, paused, offline). No-idle-workers case: all workers running → dispatched=0, assignments=[]. No-pending-tasks case: clean scenario with idle worker + zero tasks → dispatched=0, assignments=[]. max_assignments=0 clamped to 1 → dispatched=1. max_assignments=999 bounded by available worker/task pairs → dispatched=2.

3. **dispatch_state_consistency** — Task `worker_id` updated after dispatch. Task status remains `pending` (dispatch assigns, doesn't start). Worker status updated to `assigned`. Worker `current_task_id` set correctly. Already-assigned tasks not dispatched again.

4. **dispatch_safety_failure_isolation** — Output does not leak raw task goals, steps, or secret sentinels. Assignments contain only worker_id/task_id/status (no goal/steps). Broken event store does not prevent dispatch. Registry tools (get_worker, list_workers, list_durable_tasks) still work after broken event store.

## Safety Assertions

- Goal sentinel → not in output
- Secret sentinel → not in output
- Step content → not in output
- Assignments → bounded (no goal/steps fields)
- Broken event store → dispatch still works

## Diff

```text
 evals/run_evals.py | 186 ++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 186 insertions(+)
```

## Tests

```text
python3 evals/run_evals.py
186 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 468 tests in 9.430s
OK

git diff --check
(clean)
```

## Notes

- No runtime code changed — eval only as instructed.
- TASK-048 implementation was already complete.
- No commit or push performed.
- Known limitations: none.
