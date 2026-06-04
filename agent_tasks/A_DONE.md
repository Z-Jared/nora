# TASK-105 Completion Report (PM Review Fix)

## Task
Runtime policy hook event query v1

## Summary
Added read-only `list_runtime_policy_hook_evaluations(...)` registry tool for querying `policy_hook_evaluation` durable events with safe bounded metadata.

## PM Review Fixes

### 1. Expanded hook set
- **Before:** `_VALID_POLICY_HOOKS` was a subset (`pre_tool`, `pre_shell`, `pre_git`, `before_commit`, `post_test`, `before_handoff`)
- **After:** Uses `_VALID_HOOKS` from TASK-101/TASK-103: `pre_tool`, `post_tool`, `pre_edit`, `post_edit`, `pre_shell`, `pre_git`, `pre_plugin_call`, `post_test`, `before_handoff`, `before_commit`

### 2. Invalid/unsafe filters reject instead of degrade
- **Before:** Invalid `hook`/`decision` filter silently cleared to `""`, returning all events
- **After:** Non-empty invalid/unsafe filters return bounded empty result with `errors` list; raw sentinel values never leak into output
- Applies to: `hook`, `decision`, `task_id`, `worker_id`, `session_id`

### 3. New regression tests
- `test_hook_filter_post_tool`, `test_hook_filter_pre_edit`, `test_hook_filter_post_edit`, `test_hook_filter_pre_plugin_call` — all previously missing hooks now tested
- `test_invalid_hook_filter_returns_empty` — invalid hook returns 0 events + `errors`
- `test_unsafe_hook_filter_returns_empty` — secret sentinel returns 0 events + `errors`
- `test_invalid_decision_filter_returns_empty` — invalid decision returns 0 events + `errors`
- `test_unsafe_task_id_returns_empty` — secret task_id returns 0 events + `errors`

## Changes

### `mini_agent/toolkits/registry_builder.py`
- Removed `_VALID_POLICY_HOOKS`, now uses `_VALID_HOOKS` from evaluator scope
- Invalid/unsafe non-empty filters return `{events: [], count: 0, errors: [...]}` instead of degrading to all-events query

### `tests/test_durable_workers.py`
- 5 existing tests updated to match new rejection behavior
- 4 new tests added for missing hooks and rejection semantics
- Total: 29 tests in `ListRuntimePolicyHookEvaluationsTests`

## Verification
```
python3 -m unittest tests.test_durable_workers          → 665 passed
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent → 311 passed
python3 evals/run_evals.py                              → 383 passed, 0 failed
git diff --check                                        → clean
```

## Files Modified
- `mini_agent/toolkits/registry_builder.py`
- `tests/test_durable_workers.py`
