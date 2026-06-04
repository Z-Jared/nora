# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-103: Runtime policy hook evaluation event recording v1

## Context

TASK-101 added the read-only `evaluate_runtime_policy_hook(...)` registry tool. TASK-102 added deterministic eval coverage for policy decisions, bounded output, no-leak behavior, read-only behavior, and compatibility.

The next north-star step is to make hook/policy decisions traceable without changing the existing read-only evaluator:

- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 9: hooks and policies should be runtime mechanisms, not prompt conventions.
- Priority 1: durable traces should record important runtime decisions with task/session/worker linkage and safe artifact metadata.

## Goal

Add a small runtime policy hook event recording capability that records safe, bounded policy decision metadata into the durable event log.

Keep `evaluate_runtime_policy_hook` read-only and unchanged from a mutation perspective. Add a separate explicit recording tool, or an equivalently clear local pattern, so callers opt in to event creation.

## Requirements

- Add a registry tool such as `record_runtime_policy_hook_evaluation(...)` or a name consistent with local style.
- The tool should accept the same core inputs as the evaluator:
  - `hook`
  - `action=""`
  - `category=""`
  - `risk=""`
  - `reason=""`
- It may also accept optional bounded linkage fields if they fit existing durable event style:
  - `task_id=""`
  - `worker_id=""`
  - `session_id=""`
- The tool must:
  - Reuse the existing policy evaluation logic rather than duplicating decision rules.
  - Create exactly one durable event on successful supported-hook evaluation.
  - Return bounded JSON including event id/type, policy decision, safe reason label, confirmation/block flags, normalized hook/category/risk, sanitized action fields, policy version, and matched rule labels.
  - Never store or return raw `reason`, raw unknown hook values, shell commands, env/request strings, file contents, workspace paths, secrets, or arbitrary unbounded input.
  - Preserve `evaluate_runtime_policy_hook` as read-only: calling it must still create no durable events and no task/worker mutation.
  - Treat unsupported hooks as bounded validation errors and do not create an event for them, unless existing local style strongly favors recording rejected validation attempts. If you choose to record validation failures, explain why and keep the event payload safe.
- Keep implementation local and small, preferably near the existing runtime policy evaluator in the registry/toolkit code.
- Follow existing durable event naming and payload conventions. If a new event type/constant is needed, add it minimally.

## Tests

Add focused unit tests in `tests/test_durable_workers.py` or the closest existing file covering at least:

- Successful recording creates exactly one durable event with safe policy hook metadata.
- The returned event id corresponds to a queryable durable event.
- Event payload includes bounded decision fields and matched rules.
- Raw `reason` sentinel is not present in tool output or event payload.
- Secret-like action, env-like action, shell command action, and workspace path action are redacted in tool output and event payload.
- Unsupported hook returns a bounded validation error and does not leak the raw hook sentinel.
- Unsupported hook does not create an event, unless you intentionally choose a safe rejected-event behavior and test that behavior explicitly.
- `evaluate_runtime_policy_hook` remains read-only and creates no durable events.
- No durable task or worker state mutation happens from either evaluation or recording.
- Compatibility: existing registry permission/listing behavior and `confirm_action` still work.

Run:

```text
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Boundaries

- Do not wire policy recording into enforcement yet.
- Do not make normal tool execution automatically record policy hook events.
- Do not change existing policy decisions unless a test exposes a real bug; if that happens, keep the fix minimal and explain it.
- Do not edit `agent_tasks/B_TASK.md` or `agent_tasks/B_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/A_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh A
```
