# Claude B Done

Owner: Claude B
Status: completed
Task: TASK-096 Deterministic eval coverage for scheduler retry planning v1

## Summary

Added 13 deterministic offline eval cases for scheduler retry planning and explainability in `evals/run_evals.py`:

1. **retry_planner_available** — Failed task with retries remaining is surfaced as `retry_failed_task` / `retry_available`.
2. **retry_planner_exhausted** — Failed task with `retry_count >= max_retries` is not recommended for retry; `retry_exhausted` count in summary.
3. **retry_planner_blocked_active_worker** — Failed task with active ASSIGNED or RUNNING owner worker is blocked; both states explicitly covered.
4. **retry_explain_available** — Explain: retryable task with idle capacity shows `retry_available` with correct detail (`retry N/M available`).
5. **retry_explain_exhausted** — Explain: exhausted task shows `retry_exhausted` with `max retries` detail.
6. **retry_explain_blocked_active_worker** — Explain: active ASSIGNED or RUNNING worker blocks retry with `retry_blocked_active_worker` and correct worker_id; both states explicitly covered.
7. **retry_explain_missing_capacity** — Explain: no idle workers shows `retry_blocked_missing_capacity`.
8. **retry_priority_vs_closeout** — Ready closeout appears before retry in planner output.
9. **retry_priority_vs_dispatch** — Retry appears before pending-task dispatch in planner output.
10. **retry_filter_no_leak** — `task_id` filter excludes unrelated task_id and worker_id; `worker_id` filter excludes retry entries (empty worker_id) and unrelated task_id.
11. **retry_read_only_no_mutation** — Planner and explain calls do not mutate task status, retry_count, worker_id, worker status, or worker current_task_id.
12. **retry_safety_no_leak** — Planner/explain output does not leak goals, steps, failure_reason sentinel, secrets, or workspace paths.
13. **retry_compatibility** — Existing tools still work after retry planning/explain calls.

## PM Review Fixes

- Added RUNNING owner worker coverage (item 3, 6): both ASSIGNED and RUNNING states explicitly tested.
- Added `_LIFECYCLE_SENTINEL_FAILURE` sentinel and failure_reason no-leak assertions (item 12).
- Added `eval_retry_read_only_no_mutation` eval (item 11): verifies task/worker state unchanged after planner/explain calls.
- Strengthened filter assertions (item 10): added `tid2` and `w_f2` exclusion in `task_id` filter test.

## Diff (vs main)

```text
 evals/run_evals.py | 350 +++++++++++++++++++++++++++++++++++++++++++++++++++++
```

No runtime changes required.

## Tests

```text
python3 evals/run_evals.py
349 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 710 tests in 14.818s
OK

git diff --check
OK
```

## Notes

- No runtime implementation changes.
- No push was performed by Claude B.
