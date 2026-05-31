# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-019: implement durable approval event logging.

Nora is moving toward an Agent OS / Durable Runtime. User approvals and denials for permissioned tools should become first-class durable events, without storing raw arguments, reasons, prompts, or secrets.

## Scope

Add a narrow vertical slice for approval lifecycle events around `ToolRegistry.call(...)` when a tool requires confirmation.

1. Add event constants in `mini_agent/durable_events.py`:
   - `APPROVAL_REQUESTED`
   - `APPROVAL_DECIDED`
   - Include them in valid event type validation.

2. Extend `mini_agent/registry.py`:
   - Let `ToolRegistry` optionally receive an `event_store`.
   - When `tool.permission.requires_confirmation` is true, record an approval requested event before calling `confirm_action`.
   - After `confirm_action`, record an approval decided event with approved/denied status.
   - Existing behavior must remain unchanged: denied approval still logs tool cancellation and returns `已取消操作。`; approved approval still runs the handler.

3. Wire the durable event store in `mini_agent/toolkits/registry_builder.py`:
   - `build_default_registry(...)` should pass or assign the same `DurableEventStore` to `ToolRegistry`.
   - Direct `ToolRegistry(...)` construction must remain compatible without an event store.

## Payload Requirements

Event payloads must contain safe metadata only. Good examples:

- tool_name
- permission category/risk
- status: requested / approved / denied
- requires_confirmation
- argument_count
- argument_keys, if useful and safe
- reason_present boolean

Do not store:

- raw tool arguments or argument values
- raw reason text
- raw confirmation prompt
- raw command/file content/secret values
- API keys or secret-like values
- unbounded strings

Event writes must be failure-isolated. A broken durable event store must not change tool execution, confirmation behavior, tool logging, or agent behavior.

Keep this task narrow. Do not implement review events, replay, approval UI, policy engines, or eval coverage in this task.

## Suggested Tests

Add focused unit coverage in `tests/test_durable_events.py` and/or existing registry/agent tests:

1. Permissioned tool approval emits requested + decided approved events and still runs the handler.
2. Permissioned tool denial emits requested + decided denied events and preserves existing cancellation result.
3. Non-permissioned tools do not emit approval events.
4. Broken event store does not break approved or denied tool calls.
5. Serialized approval events do not contain sentinel argument values, raw reason text, raw prompt text, or secret-like values.
6. Default registry wires approval events for a permissioned tool path.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_events tests.test_mini_agent
python3 evals/run_evals.py
```

If registry behavior changes broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
