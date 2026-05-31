# Claude A Task

Owner: Claude A
Status: completed

## Goal

TASK-021: durable review-gate event logging.

Nora is moving toward an Agent OS / Durable Runtime. Review gates should become auditable durable runtime events, so future PM/reviewer workflows can inspect when staged changes were reviewed before integration.

## Scope

Add a narrow vertical slice for review-gate lifecycle events around the existing staged-diff review path.

1. Add event constants in `mini_agent/durable_events.py`:
   - `REVIEW_GATE_STARTED`
   - `REVIEW_GATE_FINISHED`
   - `REVIEW_GATE_BLOCKED`
   - `REVIEW_GATE_ERROR`
   - Include them in valid event type validation.

2. Extend `mini_agent/git_tools.py`:
   - Let `GitTools` optionally receive or be assigned an `event_store`.
   - Add failure-isolated review-gate event recording.
   - Instrument `GitTools.review_staged_diff(...)`:
     - record started before inspecting staged changes
     - record finished when review output is produced, including the no-staged-diff path
     - record error if Git command execution reports a generic Git failure
   - Preserve the existing user-visible return strings as much as possible.

3. Wire the durable event store in `mini_agent/toolkits/registry_builder.py`:
   - `build_default_registry(...)` should pass or assign the same `DurableEventStore` to `GitTools`.
   - Direct `GitTools(...)` construction must remain compatible without an event store.

## Payload Requirements

Event payloads must contain safe metadata only. Good examples:

- gate_name, e.g. `staged_diff_review`
- status: started / finished / no_diff / error / blocked
- has_staged_diff boolean
- file_count integer
- sensitive_path_count integer
- max_chars integer
- generic error label, if any

Do not store:

- raw diff content
- raw file names or paths
- raw Git command strings
- raw Git stdout/stderr
- raw sensitive path warning text
- raw exception text
- API keys or secret-like values
- unbounded strings

Event writes must be failure-isolated. A broken durable event store must not change review output or Git tool behavior.

Keep this task narrow. Do not implement reviewer agents, merge gates, commit blocking, UI, policy engines, or eval coverage in this task.

## Suggested Tests

Add focused unit coverage in `tests/test_durable_events.py`, `tests/test_git_tools.py`, and/or existing CLI/registry tests:

1. Empty staged diff emits started + finished/no_diff review-gate events.
2. Present staged diff emits started + finished events and preserves the existing review output.
3. Serialized review-gate events do not contain sentinel file content, raw diff text, raw file paths, sensitive path warning text, or secret-like values.
4. Broken event store does not break `review_staged_diff`.
5. Default registry wires `GitTools` to the durable event store so `git_review_staged_diff` emits review-gate events.
6. Direct `GitTools(...)` without an event store still behaves as before.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_events tests.test_git_tools tests.test_cli
python3 evals/run_evals.py
git diff --check
```

If Git tool or registry wiring changes broadly, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
