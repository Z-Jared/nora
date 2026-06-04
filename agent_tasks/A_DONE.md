# TASK-103 Completion Report

**Task:** Runtime policy hook evaluation event recording v1
**Status:** DONE (PM review fix applied)
**Agent:** Claude A
**Date:** 2026-06-04

## Changes Made

### `mini_agent/durable_events.py`
- Added `POLICY_HOOK_EVALUATION = "policy_hook_evaluation"` event type constant
- Added to `VALID_EVENT_TYPES` set

### `mini_agent/toolkits/registry_builder.py`
- Imported `POLICY_HOOK_EVALUATION` from `durable_events`
- Extracted evaluation logic from `_evaluate_runtime_policy_hook_json` into reusable `_evaluate_policy_hook_core()` helper
- Refactored `_evaluate_runtime_policy_hook_json` to use the helper (read-only behavior unchanged)
- Added `_sanitize_linkage_id()` helper: validates linkage IDs (task_id, worker_id, session_id) against path separators, shell metachar, secret-like tokens, all-caps tokens, length >80; returns None for unsafe values
- Added `record_runtime_policy_hook_evaluation` registry tool:
  - Accepts same inputs as evaluator: `hook`, `action`, `category`, `risk`, `reason`
  - Plus optional linkage fields: `task_id`, `worker_id`, `session_id`
  - Calls `_evaluate_policy_hook_core` for decision logic (no duplication)
  - Sanitizes all linkage IDs via `_sanitize_linkage_id()` before writing to event
  - Records exactly one `POLICY_HOOK_EVALUATION` durable event on supported hooks
  - Returns bounded JSON with event id, decision metadata, sanitized action, matched rules
  - Unsupported hooks return bounded error, no event created
  - Raw reason/secret/path/shell/env never stored or returned
  - Permission: `risk="write"` (writes durable events, consistent with other mutation tools)

### PM Review Fix (2026-06-04)
- **Problem:** `task_id`, `worker_id`, `session_id` were stored raw in events, leaking secret sentinels
- **Fix:** Added `_sanitize_linkage_id()` sanitizer; applied to all three linkage fields before event storage
- **Permission:** Changed from `risk="read"` to `risk="write"` since tool mutates durable events
- **Tests added:** 6 new tests for unsafe linkage sentinels (secret, path, shell, long values)

### `tests/test_durable_workers.py`
- Added `RuntimePolicyHookRecordingTests` class with 31 tests:
  - Successful recording creates exactly one event
  - Event id is queryable via `get_event`
  - Event payload includes decision fields and matched rules
  - Raw reason sentinel not in output or event payload
  - Secret-like, shell, env, path actions redacted in output and event
  - Safe action preserved
  - Unsupported hook returns error, no event, no raw leak
  - Safe task/worker/session linkage preserved
  - Unsafe linkage sentinels (SECRET_XYZ, path, shell, long) sanitized to None
  - `evaluate_runtime_policy_hook` remains read-only (no events)
  - No task/worker mutation from recording
  - Registry permissions (write) and confirm_action compatibility

## Verification

```
python3 -m unittest tests.test_durable_workers        → 635 passed
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent → 311 passed
python3 evals/run_evals.py                            → 373 passed
git diff --check                                      → clean
```
