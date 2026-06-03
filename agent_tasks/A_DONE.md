# Claude A — Completion Report

Owner: Claude A
Task: TASK-095 — Retryable failed-task planning for worker lifecycle scheduler v1
Status: **DONE** (includes TASK-093 blocker fixes)

## Summary

Extended `plan_worker_lifecycle_actions` and `explain_worker_lifecycle_scheduler_state` to detect and surface retryable failed tasks. Also fixed two TASK-093 blockers exposed by TASK-094 eval.

## Changes

### `mini_agent/toolkits/registry_builder.py` (+~70 lines)

**Blocker fix 1: `worker_unavailable` closeout candidate mapping**
- Added `worker_unavailable` reason handling in closeout candidate processing → maps to `worker_offline` with detail `no unsafe action`.

**Blocker fix 2: `worker_id` filter on top-level `tasks`**
- When `worker_id` filter is set, `filtered_tasks` now only includes tasks where `task.worker_id == worker_id`.
- `task_id` filter takes precedence; `worker_id` task filter is applied only when `task_id` is not set.

**Retry planning (TASK-095):**
- Planner: detects failed tasks with `retry_count < max_retries` and no active worker; adds `retry_failed_task` actions after closeouts before dispatch; adds summary fields `retryable_tasks`, `retry_exhausted`, `retry_blocked_active_worker`.
- Explain: adds blocked_reasons for `retry_available`, `retry_exhausted`, `retry_blocked_active_worker`, `retry_blocked_missing_capacity`, `retry_not_needed`; adds `retry_failed_task` next_actions.

### `tests/test_durable_workers.py` (+~290 lines)

**`RetryableTaskPlannerTests`** (7 tests): retry available, exhausted, active worker blocked, closeout priority, summary fields, no leak, no mutation.

**`RetryableTaskExplainTests`** (11 tests): retry surfaced, exhausted, active worker, missing capacity, filter no leak, retry_not_needed, no leak, no mutation, compatibility.

**`BlockerFixTests`** (4 tests):
- `test_offline_assigned_worker_returns_worker_offline` — offline worker with task → `worker_offline` in blocked_reasons.
- `test_offline_assigned_worker_no_mutation` — no state change.
- `test_worker_filter_excludes_other_worker_tasks_from_top_level` — `worker_id` filter excludes other worker's tasks from top-level `tasks`.
- `test_worker_filter_excludes_other_worker_tasks_from_planned_actions` — `worker_id` filter excludes other worker's planned actions.

## Verification

```text
Planner+Explain+Retry+Blocker (77) → OK
test_durable_workers (543) → OK
broader suite (710) → OK
git diff →check → clean
```

## Boundaries

- ✅ Only edited registry_builder.py and test_durable_workers.py
- ✅ No B_TASK/B_DONE, CODEX_TERMINAL_HANDOFF.md, designs/
- ✅ No commit/push
- ✅ Read-only planner/explain, no mutation
