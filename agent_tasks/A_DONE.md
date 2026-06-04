# Claude A Completion Report

Status: ready for Codex review

## Summary

Implemented `summarize_runtime_policy_hook_evaluations(...)` registry tool (TASK-107). This read-only tool provides an aggregate summary of recent `policy_hook_evaluation` durable events, answering "how many allow/confirm/block decisions happened recently, by hook/category/risk, and which recent safe event IDs contributed?"

### Implementation

**`mini_agent/toolkits/registry_builder.py`** — Added `_summarize_runtime_policy_hook_evaluations_json()` function and registered it as `summarize_runtime_policy_hook_evaluations`:

- Queries `policy_hook_evaluation` events from the durable event store
- Supports bounded filters: `hook`, `decision`, `category`, `risk`, `task_id`, `worker_id`, `session_id`, `limit`
- `limit` clamped to [1, 100], defaults to 20
- Invalid/unsafe non-empty filters return bounded empty summary with `errors` list (consistent with `list_runtime_policy_hook_evaluations` pattern)
- Returns bounded JSON with: `total`, `filters`, `decisions` (allow/confirm/block counts), `hooks`, `categories`, `risks`, `requires_confirmation_count`, `blocked_count`, `recent_event_ids`, `policy_versions`
- Read-only: no event creation, no task/worker mutation
- Registered with `ToolPermission(category="local", risk="read")`

**`tests/test_durable_workers.py`** — Added `SummarizeRuntimePolicyHookEvaluationsTests` class with 28 tests:

- Basic summary: empty returns zeros, decision counts, hook counts, category counts, risk counts, policy versions, recent event IDs
- Filters: hook, decision, category, risk, task_id, worker_id, session_id
- Invalid/unsafe filters: invalid hook/decision/category/risk/task_id/worker_id/session_id all return empty with errors
- Limit: bounded, clamped to max, invalid defaults, zero clamps to one
- No-leak: raw reason and action sentinels not in output
- Read-only: no event creation, no task/worker mutation
- Compatibility: evaluate, record, list, list_tool_permissions, confirm_action all still work

## Diff

```text
 mini_agent/toolkits/registry_builder.py | 135 ++++++++++++++++++++++++++++++++
 tests/test_durable_workers.py           | 198 ++++++++++++++++++++++++++++++++++++++++
 2 files changed, 333 insertions(+)
```

## Tests

```text
python3 -m unittest tests.test_durable_workers                     — 701 tests, OK
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent — 311 tests, OK
python3 evals/run_evals.py                                         — 395 passed, 0 failed
git diff --check                                                   — clean
```

## Notes

- No push performed.
- No conflicts with other workers.
- Existing evaluator, recorder, and listing tools remain unchanged and functional.
