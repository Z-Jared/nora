# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-104: Deterministic eval coverage for runtime policy hook event recording v1

## Context

TASK-103 added explicit runtime policy hook evaluation event recording:

- `mini_agent/durable_events.py` now includes `POLICY_HOOK_EVALUATION`.
- `mini_agent/toolkits/registry_builder.py` now has `record_runtime_policy_hook_evaluation(...)`.
- `evaluate_runtime_policy_hook(...)` must remain read-only and create no events.
- Recording is explicit opt-in, writes exactly one safe bounded event on supported hooks, and must not leak raw reason/action/linkage sentinels.

The next north-star step is deterministic offline eval coverage for this traceability behavior:

- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 9: hook/policy kernel.
- Priority 1: durable traces should record important runtime decisions with safe metadata.

## Goal

Add deterministic offline eval coverage for TASK-103's runtime policy hook event recording tool.

This is an eval/test coverage task. Avoid runtime behavior changes unless an eval exposes a real bug. If you find a bug, keep the fix minimal and explain it in `agent_tasks/B_DONE.md`.

## Requirements

Add focused eval cases, preferably in `evals/run_evals.py` alongside existing policy hook evals, covering:

- Successful `record_runtime_policy_hook_evaluation` creates exactly one `policy_hook_evaluation` event.
- Event payload includes bounded decision fields: decision, requires_confirmation, blocked, reason_label, policy_version, matched_rules, normalized hook/category/risk, and safe action metadata.
- Returned event id is queryable via the durable event store.
- Raw `reason` sentinel is absent from tool output and event payload.
- Secret-like action, env-like action, shell command action, and workspace path action are redacted in both output and event payload.
- Safe action labels remain preserved when appropriate.
- Unsupported hook returns bounded error, does not include raw hook sentinel, and creates no event.
- Linkage fields preserve safe IDs and sanitize unsafe task/worker/session sentinels.
- `evaluate_runtime_policy_hook` remains read-only and creates no events.
- No durable task or worker mutation happens from either evaluation or recording.
- Compatibility: existing `evaluate_runtime_policy_hook`, `list_tool_permissions`, and `confirm_action` behavior still work.

## Verification

Run:

```text
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
git diff --check
```

## Boundaries

- Do not wire policy recording into enforcement.
- Do not make normal tool execution automatically record policy hook events.
- Do not broaden policy decisions unless a focused eval exposes a real bug.
- Do not edit `agent_tasks/A_TASK.md` or `agent_tasks/A_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/B_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh B
```
