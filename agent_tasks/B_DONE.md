# B DONE — TASK-104

## Status: DONE

## What changed

Added 10 deterministic offline eval cases in `evals/run_evals.py` covering `record_runtime_policy_hook_evaluation` (TASK-103):

| Eval | Coverage |
|------|----------|
| `policy_hook_record_creates_event` | Exactly one `policy_hook_evaluation` event created; event_id matches output |
| `policy_hook_record_event_fields` | Event payload has bounded decision fields (decision, requires_confirmation, blocked, reason_label, policy_version, matched_rules, normalized hook/category/risk, safe action metadata); output matches event |
| `policy_hook_record_event_queryable` | Returned event_id is queryable via `get_event()` |
| `policy_hook_record_reason_no_leak` | Raw reason sentinel absent from both output and event payload |
| `policy_hook_record_action_redaction` | Secret/env/shell/path actions redacted in output and event payload; safe labels preserved |
| `policy_hook_record_unsupported_no_event` | Unsupported hook returns bounded error, no raw hook echo, no event created |
| `policy_hook_record_linkage_sanitize` | Safe IDs preserved; secret-like/path/long IDs sanitized to None/empty |
| `policy_hook_evaluate_still_read_only` | `evaluate_runtime_policy_hook` creates no events (read-only) |
| `policy_hook_record_no_mutation` | No task/worker mutation from evaluation or recording |
| `policy_hook_record_compatibility` | Existing tools (`list_tool_permissions`, `evaluate_runtime_policy_hook`, durable tasks, event store) still work |

## PM review fix

Initial evals used `list_events()[-1]` to fetch events, which assumed insertion order. Durable event store ordering is not guaranteed. Fixed all event lookups to use `get_event(event_id)` from the tool's returned JSON, ensuring precise event retrieval regardless of store ordering.

## Tests run

```
python3 evals/run_evals.py                    → 383 passed, 0 failed
python3 -m unittest tests.test_durable_workers → 635 tests OK
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent → 311 tests OK
git diff --check                              → clean
```

## Notes

- No runtime changes needed; TASK-103 implementation is correct.
- Only `evals/run_evals.py` modified.
- No commit/push performed.
