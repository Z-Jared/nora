# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-107: Runtime policy hook decision summary v1

## Context

TASK-101 added the read-only `evaluate_runtime_policy_hook(...)` tool. TASK-103 added explicit policy hook event recording. TASK-105 added `list_runtime_policy_hook_evaluations(...)`, and TASK-106 added deterministic eval coverage for that query tool.

The next step is an aggregate view for PM/UI workflows:

- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 1: durable traces should record and expose important runtime decisions.
- Priority 9: hook/policy decisions should be runtime-backed, testable, and traceable.
- Priority 10: Agent OS UI needs concise summaries of task/runtime decisions.

Existing `list_runtime_policy_hook_evaluations(...)` is useful for recent event inspection. PM/UI workflows also need a small policy-specific read-only summary that answers "how many allow/confirm/block decisions happened recently, by hook/category/risk, and which recent safe event IDs contributed?"

## Goal

Add a read-only registry tool for summarizing recent runtime policy hook evaluation events.

Suggested name: `summarize_runtime_policy_hook_evaluations(...)`.

## Requirements

The tool should:

- Query durable events of type `policy_hook_evaluation`.
- Be read-only: no durable task, worker, file, shell, git, browser, or event mutation.
- Support bounded filters:
  - `hook=""`
  - `decision=""`
  - `category=""`
  - `risk=""`
  - `task_id=""`
  - `worker_id=""`
  - `session_id=""`
  - `limit=20`
- Clamp/validate `limit` consistently with local style, with a small maximum such as 100.
- Return bounded JSON with:
  - `total`: number of included policy hook events
  - normalized filters used
  - `decisions`: counts for `allow`, `confirm`, and `block`
  - `hooks`: bounded counts by supported hook
  - `categories`: bounded counts by safe category label
  - `risks`: bounded counts by safe risk label
  - `requires_confirmation_count`
  - `blocked_count`
  - `recent_event_ids`: bounded list of event IDs included in newest-first order
  - `policy_versions`: bounded counts by safe policy version
- Never return raw `reason`, raw unsupported hook values, shell commands, env/request strings, file contents, workspace paths, secrets, raw actions, or unbounded payload.
- Invalid/unsafe non-empty filters should return a bounded empty summary with safe errors instead of degrading to all-events.
- Preserve existing `evaluate_runtime_policy_hook`, `record_runtime_policy_hook_evaluation`, and `list_runtime_policy_hook_evaluations` behavior.

Implementation should stay local near the existing policy hook evaluator/recorder/listing code in `mini_agent/toolkits/registry_builder.py`.

## Tests

Add focused unit tests, likely in `tests/test_durable_workers.py`, covering:

- Summary counts for allow/confirm/block, hooks, categories, risks, confirmation count, blocked count, policy versions, and recent event IDs.
- `hook`, `decision`, `category`, `risk`, `task_id`, `worker_id`, and `session_id` filters work.
- `limit` is bounded and deterministic.
- Invalid/unsafe filters return empty safe summaries with errors and do not return all events.
- Raw reason/action/linkage sentinels do not appear in output.
- The summary tool is read-only and does not create events or mutate tasks/workers.
- Compatibility: existing evaluator, recorder, listing tool, `list_tool_permissions`, and `confirm_action` still work.

Run:

```text
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Boundaries

- Do not add enforcement wiring.
- Do not auto-record normal tool execution.
- Do not change existing policy decisions unless a test exposes a real bug; if so, keep the fix minimal and explain it.
- Do not edit `agent_tasks/B_TASK.md` or `agent_tasks/B_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/A_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh A
```
