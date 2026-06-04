# TASK-106: Deterministic eval coverage for runtime policy hook event query v1

## Status: DONE (PM review fix applied)

## Changes

### `evals/run_evals.py`
Added 12 eval cases for `list_runtime_policy_hook_evaluations` (TASK-105), with PM review fixes:

1. **policy_hook_query_lists_events** - Verifies recorded events are returned with safe bounded metadata, matching event IDs, and **newest-first ordering** (consistent with DurableEventStore's `ORDER BY rowid DESC`).
2. **policy_hook_query_filter_hook** - Hook filter returns only matching events.
3. **policy_hook_query_filter_decision** - Decision filter (allow/confirm) returns only matching events.
4. **policy_hook_query_filter_linkage** - task_id, worker_id, session_id filters work correctly.
5. **policy_hook_query_filter_combined** - Combined filters narrow results correctly.
6. **policy_hook_query_limit** - Limit parameter bounds returned events; clamps to [1, 100].
7. **policy_hook_query_invalid_hook_filter** - Invalid hook returns empty result with error, not all events.
8. **policy_hook_query_invalid_decision_filter** - Invalid decision returns empty result with error, not all events.
9. **policy_hook_query_unsafe_linkage_filter** - Unsafe linkage filters (path/secret/shell metachar) return empty result with error.
10. **policy_hook_query_reason_no_leak** - Raw reason sentinel (`reason="RAW_REASON_SENTINEL_XYZ_789"`) **and** action/shell/env sentinels do not leak in query output.
11. **policy_hook_query_read_only_no_mutation** - Query creates no events; does not mutate tasks **or workers** (registers worker, checks count and status before/after query).
12. **policy_hook_query_compatibility** - Tool is registered and compatible with evaluate/record/durable task tools.

Also added helper function `_record_policy_hook_events()` for test setup.

## PM Review Fixes
- **Sorting/recency**: Added explicit assertions that first returned event = last recorded, last returned = first recorded (newest-first).
- **Raw reason no-leak**: Added `reason="RAW_REASON_SENTINEL_XYZ_789"` to recorded event, assert sentinel absent from query output.
- **Worker no-mutation**: Register worker before query, compare worker count and individual worker status before/after.

## Test Results

```
python3 evals/run_evals.py: 395 passed, 0 failed
python3 -m unittest tests.test_durable_workers: 665 tests OK
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent: 311 tests OK
git diff --check: clean
```

## Notes
- No runtime changes needed; TASK-105 implementation is correct.
