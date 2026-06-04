# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-110: Deterministic eval coverage for runtime policy hook rule catalog v1

## Context

TASK-109 added the read-only `describe_runtime_policy_hook_rules(...)` registry tool. It returns a safe bounded JSON catalog for the runtime policy hook kernel: `policy_version`, supported hooks/categories/risks/decisions, and stable rule metadata that explains the current `_evaluate_policy_hook_core` priority order.

The next Agent OS step is deterministic offline eval coverage for this rule catalog, so future UI/trace/enforcement work can trust the policy catalog contract without source-code inspection.

## Goal

Add deterministic eval coverage in `evals/run_evals.py` for `describe_runtime_policy_hook_rules(...)`.

## Requirements

Add focused offline eval cases that verify:

- Tool registration and read-only permission via `list_tool_permissions`.
- Output includes `policy_version`.
- Supported `hooks`, `categories`, `risks`, and `decisions` are present, complete, and sorted.
- `rules` is bounded, deterministic, and contains the expected stable rule IDs:
  - `rule_deny_destructive_external`
  - `rule_high_risk_confirm`
  - `rule_pre_shell_write`
  - `rule_pre_git_write`
  - `rule_before_commit_write`
  - `rule_pre_tool_write`
  - `rule_pre_tool_read`
  - `rule_read_allow`
  - `rule_write_confirm`
  - `rule_default_allow`
- Known rule metadata matches current evaluator behavior: decision, hook coverage, risk coverage, `reason_label`, `requires_confirmation`, and `blocked`.
- Catalog priority matches evaluator priority for key cases:
  - destructive/external_send block before hook-specific rules
  - high risk confirms before hook-specific write rules
  - pre-shell/pre-git/before-commit/pre-tool write confirmation
  - pre-tool read allow
  - generic read allow
  - generic write confirmation
  - unknown/default allow
- Output does not leak raw action, raw reason, shell commands, file/workspace paths, env/request strings, secrets, task goals, event payloads, or user-provided input.
- Tool is read-only and does not create durable events or mutate durable tasks/workers.
- Compatibility: existing `evaluate_runtime_policy_hook`, `record_runtime_policy_hook_evaluation`, `list_runtime_policy_hook_evaluations`, `summarize_runtime_policy_hook_evaluations`, `list_tool_permissions`, durable event store, and existing evals still work.

Keep the evals deterministic and offline: use temporary directories/local `NoraDB`, no network, no model calls, no shared state.

## Tests

Run:

```text
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
git diff --check
```

## Boundaries

- Do not change runtime behavior unless an eval exposes a real TASK-109 bug; if needed, keep the fix minimal and explain it in `B_DONE.md`.
- Do not edit `agent_tasks/A_TASK.md` or `agent_tasks/A_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/B_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh B
```
