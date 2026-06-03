# CCB Code Review Report

Reviewed: TASK-094 — Deterministic eval coverage for scheduler blocker explanation v1
Worker: Claude B
Status: **APPROVED**

---

## 1. Eval Coverage (13 cases)

All 13 evals have substantive assertions covering the required scenarios:

| # | Eval | Key Assertions |
|---|------|---------------|
| 1 | `explain_empty_state` | `total_workers==0`, `total_tasks==0`, exactly 1 reason `"no_action_needed"` with correct detail |
| 2 | `explain_ready_closeout` | `ready_closeout` reason with correct `worker_id`/`task_id`, `"finalize"` in detail, `finalize_ready_workspace_merge` next action |
| 3 | `explain_not_ready_closeout` | Not-ready worker has blocked reason from expected set (`waiting_for_workspace_merge_apply`, `missing_active_lease`, etc.) |
| 4 | `explain_dispatch_available` | `dispatch_available` reason with specific worker_id, `detail=="dispatch_blocked_in_scheduler"`, `dispatch_pending_task` next action |
| 5 | `explain_pending_no_idle_workers` | `pending_task_unassigned` reason with `detail=="no_idle_workers"` |
| 6 | `explain_idle_no_pending` | Idle worker has `"no_pending_tasks"` reason |
| 7 | `explain_offline_worker` | Offline worker has `"worker_offline"` reason |
| 8 | `explain_worker_filter` | `worker_id` filter: all reasons match filtered worker, all workers output match |
| 9 | `explain_task_filter` | `task_id` filter: all reasons match filtered task, all tasks output match |
| 10 | `explain_filter_no_leak` | Two ready workers, filter by one → other worker_id absent from full JSON output; two tasks, filter by one → other task_id absent |
| 11 | `explain_limit_clamp_and_bad_args` | Bad `worker_id`/`task_id`/`limit` types → error; `limit=0→1`, `limit=999→100` |
| 12 | `explain_safety_no_leak` | 8 sentinels (goal, secret, step, file, reviewer, shell, request, env) + `.workspaces` path fragment all absent |
| 13 | `explain_compatibility` | Planner, tick, loop, run-once, closeout query, worker/task registry, claim, dispatch all still work |

**Verdict: ✅ All evals have substantive assertions.**

---

## 2. Runtime Fix (3 lines)

```python
# When task_id filter is set, also filter workers to those assigned to that task
if task_id:
    filtered_workers = [w for w in filtered_workers if w.current_task_id == task_id]
```

**Analysis:**
- Placed after `filtered_tasks` logic, before `workers_out` generation
- Only activates when `task_id` is set (no effect on `worker_id` filter or unfiltered calls)
- Filters by `current_task_id == task_id` — a worker is relevant to a task only if assigned to it
- Cannot hide relevant workers: a worker with `current_task_id` matching the requested task is the only worker that matters for that task's explanation
- `worker_id` filter already narrows workers at line 3707, so this fix only affects the `task_id`-only filter path

**Verdict: ✅ Correct, no risk of hiding relevant workers.**

---

## 3. Output Safety

- ✅ Read-only: `explain_worker_lifecycle_scheduler_state` is registered with `task/read` permission, `requires_confirmation=False`
- ✅ Bounded: output contains only `scheduler`, `filters`, `limit`, `summary`, `workers`, `tasks`, `closeout_candidates`, `planned_actions`, `blocked_reasons`, `next_actions`
- ✅ No-leak: `eval_explain_safety_no_leak` verifies 8 sentinels + workspace path fragment absent
- ✅ Filter no-leak: `eval_explain_filter_no_leak` verifies unrelated worker/task data excluded from filtered output

---

## 4. Missing Eval or Runtime Fix?

None identified. The 13 evals cover all scenarios listed in the task description. The 3-line runtime fix is minimal and correct.

---

## Checks

```text
python3 evals/run_evals.py → 336 passed, 0 failed
python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent → 710 OK
git diff --check → clean
```

---

## Findings

### Must Fix

None.

### Notes

- `eval_explain_not_ready_closeout` asserts reason is in a set of 4 possibilities (`waiting_for_workspace_merge_apply`, `missing_active_lease`, `worker_running`, `task_not_running`). This is slightly loose but acceptable since the exact reason depends on the not-ready worker's state, which is set up by `_setup_lifecycle_not_ready_worker`.

---

## Residual Risk

None. The evals are deterministic (tempfile isolation, no LLM calls), the runtime fix is minimal and correct, and the output is bounded/no-leak.

---

## Recommendation

**APPROVE and merge.**
