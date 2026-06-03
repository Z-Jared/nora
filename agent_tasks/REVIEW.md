# CCB Code Review Report

Reviewed: TASK-096 — Deterministic eval coverage for scheduler retry planning v1
Worker: Claude B
Status: **APPROVED**

---

## 1. Coverage of TASK-096 Requirements

All 13 evals cover the required scenarios with substantive assertions:

| # | Eval | Key Assertions |
|---|------|---------------|
| 1 | `retry_planner_available` | `retry_failed_task` action present with `task_id==tid`, `reason=="retry_available"`, `retry_count==0`, `max_retries==3` |
| 2 | `retry_planner_exhausted` | No retry action for exhausted task; `summary.retry_exhausted >= 1` |
| 3 | `retry_planner_blocked_active_worker` | Both ASSIGNED and RUNNING owner cases: no retry action, `summary.retry_blocked_active_worker >= 1` |
| 4 | `retry_explain_available` | `retry_available` reason with `"retry 2/3"` in detail; `retry_failed_task` next action present |
| 5 | `retry_explain_exhausted` | `retry_exhausted` reason with `"max retries"` in detail |
| 6 | `retry_explain_blocked_active_worker` | Both ASSIGNED and RUNNING: `retry_blocked_active_worker` reason with correct `worker_id` and `"active"` in detail |
| 7 | `retry_explain_missing_capacity` | `retry_blocked_missing_capacity` reason with `"no idle workers"` in detail |
| 8 | `retry_priority_vs_closeout` | `closeout_idx < retry_idx` (index comparison) |
| 9 | `retry_priority_vs_dispatch` | `retry_idx < dispatch_idx` (index comparison) |
| 10 | `retry_filter_no_leak` | `task_id` filter: tid2/w_f2 absent from full JSON; `worker_id` filter: retry entries (empty worker_id) excluded, tid2/w_f2 absent |
| 11 | `retry_read_only_no_mutation` | 5 fields (status, retry_count, worker_id, worker status, current_task_id) unchanged after planner AND explain |
| 12 | `retry_safety_no_leak` | 5 sentinels (goal, secret, step, failure_reason) + workspace path absent from planner AND explain output |
| 13 | `retry_compatibility` | Planner, explain, tick, loop, run-once, registry, claim, dispatch all still work |

**PM fixes verified:**
- ✅ RUNNING owner explicitly tested (items 3, 6)
- ✅ `_LIFECYCLE_SENTINEL_FAILURE` sentinel added and asserted absent (item 12)
- ✅ `eval_retry_read_only_no_mutation` covers both planner and explain (item 11)
- ✅ Filter assertions strengthened with tid2/w_f2 exclusion (item 10)

---

## 2. Deterministic/Offline

- ✅ All evals use `tempfile.TemporaryDirectory()` for isolation
- ✅ No external API calls
- ✅ No timing dependencies
- ✅ Ordering assertions use index comparison (`closeout_idx < retry_idx`), not incidental ordering
- ✅ `_setup_failed_task` helper properly cycles through `retry_durable_task` to set `retry_count`

---

## 3. Weak Assertions

None identified. All assertions are substantive:
- Negative assertions (no retry action when exhausted/blocked) paired with positive summary counts
- Specific string matching (`"retry 2/3"`, `"max retries"`, `"active"`, `"no idle workers"`)
- Full JSON string search for leaked IDs in filter tests
- 5-field before/after comparison in no-mutation test
- 5 sentinels + workspace path in safety test

---

## 4. Runtime Fix

None needed. Eval-only changes.

---

## Checks

```text
python3 evals/run_evals.py → 349 passed, 0 failed
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent → 710 OK
git diff --check → clean
```

---

## Findings

### Must Fix

None.

### Notes

- Minor typo in B_DONE.md: `_LIFECECYCLE_SENTINEL_FAILURE` (should be `_LIFECYCLE_SENTINEL_FAILURE`). The actual code uses the correct spelling.
- `retry_filter_no_leak` asserts retry entries are excluded by `worker_id` filter because retry reasons have empty `worker_id`. This is correct behavior but worth noting: retry entries are task-level, not worker-level.

---

## Residual Risk

None. Evals are deterministic, offline, and cover all required scenarios with substantive assertions.

---

## Recommendation

**APPROVE and merge.**
