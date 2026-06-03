# CCB Code Review Report

Reviewed: TASK-095 Retryable failed-task planning for worker lifecycle scheduler v1
Worker: Claude A
Status: **APPROVED**

---

## Review Scope

### 1. Retry Logic Correctness

**Verdict: ✅ CORRECT**

**Retryable detection (registry_builder.py planner):**
```python
failed_tasks = [t for t in tasks if t.status == "failed"]
retryable_tasks = []
for t in failed_tasks:
    if t.retry_count >= t.max_retries:
        retry_exhausted_count += 1
        continue
    # Check if an active/running worker is still attached
    owner_worker = None
    for w in workers:
        if w.current_task_id == t.task_id and w.status in (WorkerStatus.RUNNING, WorkerStatus.ASSIGNED):
            owner_worker = w
            break
    if owner_worker:
        retry_blocked_count += 1
        continue
    retryable_tasks.append(t)
```

**Semantic correctness:**
- ✅ Checks `t.status == "failed"` — only failed tasks considered
- ✅ Checks `t.retry_count >= t.max_retries` — exhausted retries excluded
- ✅ Checks active worker (`RUNNING` or `ASSIGNED`) still attached — prevents retry while worker active
- ✅ Uses existing `DurableTask.retry_count` and `DurableTask.max_retries` fields
- ✅ Consistent with `retry_durable_task` semantics (which increments retry_count)

### 2. Planner Action Ordering

**Verdict: ✅ CORRECT**

**Ordering: closeout > retry > dispatch**

```python
# Closeouts added first (existing code)
for w in ready_closeout_workers:
    actions.append({"action": "finalize_ready_workspace_merge", ...})

# Retry actions come after closeouts, before dispatch
for t in retryable_tasks:
    if len(actions) >= limit:
        break
    actions.append({"action": "retry_failed_task", ...})

# Dispatch comes last (existing code)
if idle_workers and pending_tasks and len(actions) < limit:
    actions.append({"action": "dispatch_pending_task", ...})
```

**Verified by test:**
- ✅ `test_closeout_priority_ahead_of_retry`: Creates ready closeout + failed task, verifies `finalize_ready_workspace_merge` index < `retry_failed_task` index

**Read-only planner:**
- ✅ Planner only adds `retry_failed_task` actions to plan
- ✅ Does NOT execute `retry_durable_task` (no mutation)
- ✅ `test_no_mutation` verifies task status and retry_count unchanged after planning

### 3. Explain Output Safety

**Verdict: ✅ SAFE AND BOUNDED**

**Retry reasons in explain output:**
- ✅ `retry_available` — task is retryable, idle workers exist
- ✅ `retry_exhausted` — max retries reached
- ✅ `retry_blocked_active_worker` — worker still active on task
- ✅ `retry_blocked_missing_capacity` — no idle workers available
- ✅ `retry_not_needed` — task not in failed status (when task_id filter set)

**Retry next_actions:**
- ✅ `retry_failed_task` with worker_id="", task_id, reason="retry_available"

**Filter compatibility:**
- ✅ `task_id` filter: retry reasons/actions only for matching task_id
- ✅ `worker_id` filter: retry reasons/actions preserved (worker_id="" entries allowed)
- ✅ No leak of unrelated retry actions when filter set

**Safety assertions:**
- ✅ `test_no_goal_leak_in_retry`: Sentinel goal absent from planner output
- ✅ `test_no_goal_leak`: Sentinel goal absent from explain output
- ✅ `test_no_steps_leak`: Step text absent from explain output
- ✅ `test_task_filter_no_leak_unrelated_retry`: task_id filter excludes unrelated retry reasons

### 4. TASK-093 Blocker Fixes

**Verdict: ✅ CORRECT**

**Blocker fix 1: `worker_unavailable` → `worker_offline`**
```python
elif c.get("reason") == "worker_unavailable":
    blocked_reasons.append({
        "worker_id": wid, "task_id": tid,
        "reason": "worker_offline",
        "detail": "no unsafe action",
    })
```
- ✅ Maps `worker_unavailable` closeout candidate reason to `worker_offline` in blocked_reasons
- ✅ Consistent with existing `worker_offline` handling
- ✅ `test_offline_assigned_worker_returns_worker_offline` verifies mapping

**Blocker fix 2: `worker_id` filter on top-level tasks**
```python
if task_id:
    filtered_tasks = [t for t in all_tasks if t.task_id == task_id]
elif worker_id:
    filtered_tasks = [t for t in all_tasks if t.worker_id == worker_id]
else:
    filtered_tasks = list(all_tasks)
```
- ✅ `task_id` filter takes precedence (existing behavior)
- ✅ `worker_id` filter applied only when `task_id` not set
- ✅ `test_worker_filter_excludes_other_worker_tasks_from_top_level` verifies: w1 filter → only w1's tasks in top-level `tasks`
- ✅ `test_worker_filter_excludes_other_worker_tasks_from_planned_actions` verifies: w1 filter → no w2/dtask_2 in planned_actions

### 5. Test Coverage

**Verdict: ✅ COMPREHENSIVE**

**`RetryableTaskPlannerTests` (7 tests):**
1. `test_failed_task_with_retries_remaining_is_retryable` — retry_count < max_retries → retry_failed_task action
2. `test_failed_task_exhausted_retries_not_recommended` — retry_count >= max_retries → no retry action
3. `test_failed_task_with_active_worker_is_blocked` — RUNNING/ASSIGNED worker → no retry action
4. `test_closeout_priority_ahead_of_retry` — closeout actions before retry actions
5. `test_retry_summary_fields` — summary contains retryable_tasks, retry_exhausted, retry_blocked_active_worker
6. `test_no_goal_leak_in_retry` — sentinel goal absent from planner output
7. `test_no_mutation` — task status/retry_count unchanged after planning

**`RetryableTaskExplainTests` (11 tests):**
8. `test_retryable_failed_task_surfaced` — retry_available in blocked_reasons, retry_failed_task in next_actions
9. `test_exhausted_retry_not_recommended` — retry_exhausted in blocked_reasons
10. `test_active_worker_blocks_retry` — retry_blocked_active_worker in blocked_reasons
11. `test_missing_capacity_blocks_retry` — retry_blocked_missing_capacity in blocked_reasons
12. `test_task_filter_no_leak_unrelated_retry` — task_id filter excludes unrelated retry reasons
13. `test_non_failed_task_retry_not_needed` — retry_not_needed for non-failed task
14. `test_no_goal_leak` — sentinel goal absent
15. `test_no_steps_leak` — step text absent
16. `test_no_mutation` — task status/retry_count unchanged
17. `test_compatibility_with_planner` — explain works after planner
18. `test_compatibility_with_tick_loop` — explain works after tick/loop

**`BlockerFixTests` (4 tests):**
19. `test_offline_assigned_worker_returns_worker_offline` — worker_unavailable → worker_offline mapping
20. `test_offline_assigned_worker_no_mutation` — no state change
21. `test_worker_filter_excludes_other_worker_tasks_from_top_level` — worker_id filter on tasks
22. `test_worker_filter_excludes_other_worker_tasks_from_planned_actions` — worker_id filter on actions

---

## Checks Run

```text
Planner+Explain+Retry+Blocker (77) → OK
test_durable_workers (543) → OK
broader suite (710) → OK
python3 evals/run_evals.py → 323 passed, 0 failed
git diff --check → clean
```

---

## Findings

### Must Fix

**None** — implementation is production-ready.

### Suggestions

**None** — code quality is high, no technical debt introduced.

---

## Residual Risk

**None identified.**

All critical retryable-task behaviors are covered:
- ✅ Retry logic (retry_count/max_retries, active worker check)
- ✅ Action ordering (closeout > retry > dispatch)
- ✅ Explain output (5 retry reasons, filter compatibility)
- ✅ Blocker fixes (worker_unavailable mapping, worker_id task filter)
- ✅ Safety (no goal/steps leak, no mutation)
- ✅ Compatibility (planner, tick, loop)

---

## Recommendation

**APPROVE and merge.**

TASK-095 correctly extends planner and explain to surface retryable failed tasks using existing DurableTask retry semantics. Action ordering is correct (closeout > retry > dispatch). Explain output is bounded/safe with proper filter compatibility. TASK-093 blocker fixes are correct. Comprehensive test coverage (22 new tests). No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
