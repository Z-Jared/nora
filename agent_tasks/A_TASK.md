# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-105: Runtime policy hook event query v1

## Context

TASK-101 added the read-only `evaluate_runtime_policy_hook(...)` tool. TASK-103 added explicit event recording via `record_runtime_policy_hook_evaluation(...)`. TASK-104 added deterministic eval coverage for the recorder.

The next step is trace inspectability for policy decisions:

- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 1: durable traces should record and expose important runtime decisions.
- Priority 9: hook/policy decisions should be runtime-backed, testable, and traceable.

Existing generic `list_durable_events` exists, but PM/UI workflows need a small policy-specific read-only view that returns only safe bounded policy hook evaluation metadata.

## Goal

Add a read-only registry tool for listing recent runtime policy hook evaluation events.

Suggested name: `list_runtime_policy_hook_evaluations(...)`.

## Requirements

The tool should:

- Query durable events of type `policy_hook_evaluation`.
- Be read-only: no durable task, worker, file, shell, git, browser, or event mutation.
- Support bounded filters:
  - `hook=""`
  - `decision=""`
  - `task_id=""`
  - `worker_id=""`
  - `session_id=""`
  - `limit=20`
- Clamp/validate `limit` consistently with local style, with a small maximum such as 100.
- Return bounded JSON with:
  - `events`: list of safe summaries
  - `count`
  - normalized filters used
- Each event summary should include safe fields only:
  - `event_id`, `created_at`, `task_id`, `worker_id`, `session_id`
  - `hook`, `decision`, `requires_confirmation`, `blocked`
  - `reason_label`, `policy_version`, `matched_rules`
  - `category`, `risk`, `action`, `action_label`, `action_present`
- Never return raw `reason`, raw unsupported hook values, shell commands, env/request strings, file contents, workspace paths, secrets, or unbounded payload.
- Ignore or safely normalize invalid/unknown filter values rather than leaking raw sentinels.
- Preserve existing `evaluate_runtime_policy_hook` and `record_runtime_policy_hook_evaluation` behavior.

Implementation should stay local near the existing policy hook evaluator/recorder code in `mini_agent/toolkits/registry_builder.py`.

## Tests

Add focused unit tests, likely in `tests/test_durable_workers.py`, covering:

- Listing returns recent recorded policy hook events with safe metadata.
- `hook`, `decision`, `task_id`, `worker_id`, and `session_id` filters work.
- `limit` is bounded and rejects or clamps invalid values according to local style.
- Raw reason/action/linkage sentinels do not appear in output.
- Unsupported or unsafe filter sentinels do not leak raw strings.
- The query tool is read-only and does not create events or mutate tasks/workers.
- Compatibility: existing evaluator, recorder, `list_tool_permissions`, and `confirm_action` still work.

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
