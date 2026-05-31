# Claude A Completion Report

Owner: Claude A
Task: TASK-019 — Durable approval event logging
Status: DONE

## Summary

Implemented durable approval event logging around permissioned tool confirmation in `ToolRegistry.call()`. Two new event types (`approval_requested`, `approval_decided`) record safe metadata when a tool requires user confirmation.

## Review Feedback Addressed

Reviewer requested strengthened safety tests. Updated `test_approval_event_no_raw_argument_values` to:
- Serialize full event via `event.to_dict()` JSON (not just payload)
- Assert raw argument values, raw reason text, secret sentinels, and confirmation prompt fragments absent from full serialized JSON
- Retain payload-level assertions as defense-in-depth
- Runtime verified clean — no changes needed to runtime code

## Changes

### `mini_agent/durable_events.py`
- Added `APPROVAL_REQUESTED` and `APPROVAL_DECIDED` constants
- Added them to `VALID_EVENT_TYPES`

### `mini_agent/registry.py`
- Added `event_store` parameter to `ToolRegistry.__init__`
- Imported `APPROVAL_REQUESTED` and `APPROVAL_DECIDED` from `durable_events`
- Added `_record_approval_requested()` — records event before `confirm_action` with safe metadata (tool_name, category, risk, requires_confirmation, argument_count, argument_keys, reason_present)
- Added `_record_approval_decided()` — records event after `confirm_action` with approved/denied status
- Both methods wrapped in try/except — failures never break tool execution or confirmation behavior

### `mini_agent/toolkits/registry_builder.py`
- `build_default_registry()` now passes `durable_event_store` to `ToolRegistry(event_store=durable_event_store)`

### `tests/test_durable_events.py`
- Added `ApprovalDurableEventTests` class with 10 tests:
  - `test_approval_emits_requested_and_decided_approved` — approved path records both events
  - `test_approval_emits_requested_and_decided_denied` — denied path records both events, severity=warning
  - `test_non_permissioned_tool_emits_no_approval_events` — non-confirmation tools emit nothing
  - `test_broken_event_store_does_not_break_approved_tool` — broken store doesn't prevent approval
  - `test_broken_event_store_does_not_break_denied_tool` — broken store doesn't prevent denial
  - `test_approval_event_no_raw_argument_values` — full `to_dict()` JSON serialization check: no raw args, reason, secrets, or confirmation prompt fragments
  - `test_approval_event_contains_safe_metadata` — payload has all expected safe fields
  - `test_default_registry_wires_approval_events` — default registry wires event_store
  - `test_no_event_store_does_not_break_confirmation` — no event_store doesn't break confirmation
  - `test_approval_event_reason_present_false_when_no_reason` — reason_present=false when absent

## Tests Run

```text
python3 -m unittest tests.test_durable_events tests.test_mini_agent  → 223 passed
python3 evals/run_evals.py                                           → 113 passed, 0 failed
```

## Design Notes

- Event payloads contain only safe metadata: tool_name, category, risk, requires_confirmation, argument_count, argument_keys (sorted key names only), reason_present boolean
- No raw arguments, argument values, reason text, confirmation prompt, command/file content, or secrets stored
- Event writes wrapped in try/except — failures never change tool execution, confirmation behavior, tool logging, or agent behavior
- `ToolRegistry` without `event_store` behaves identically to before
- Existing cancellation logger behavior preserved: denied approval still logs tool cancellation and returns `已取消操作。`

## Known Limitations

- `argument_keys` includes key names but not values — useful for debugging but limited for full audit
- Approval events are recorded at the registry level, not linked to task_id or trace_id
- No eval coverage added (out of scope per task instructions)

## Notes

- No push performed by Claude A.
- No commit performed by Claude A.
