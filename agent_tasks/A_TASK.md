# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-109: Runtime policy hook rule catalog v1

## Context

TASK-101 through TASK-108 added a read-only runtime policy hook evaluator, explicit policy hook evaluation event recording, event listing, summary aggregation, and deterministic eval coverage.

The next Agent OS step is making the hook/policy kernel inspectable. UI, trace, and future enforcement paths need a safe way to ask "what hooks, categories, risks, decisions, and rules does this policy version support?" without depending on source-code reading or raw prompts.

## Goal

Add a read-only registry tool that returns a safe bounded JSON catalog of the runtime policy hook rules.

Suggested tool name:

```text
describe_runtime_policy_hook_rules
```

## Requirements

- Return `policy_version`.
- Return sorted supported `hooks`, `categories`, `risks`, and `decisions`.
- Return a bounded `rules` list with stable rule IDs already used by `_evaluate_policy_hook_core`, plus safe metadata such as:
  - `rule_id`
  - `decision`
  - `hooks` or `hook`
  - `risks`
  - `reason_label`
  - `requires_confirmation`
  - `blocked`
  - short safe `description`
- Include enough rules to explain current evaluator behavior:
  - destructive/external-send block
  - high-risk confirmation
  - pre-shell write confirmation
  - pre-git write confirmation
  - before-commit write confirmation
  - pre-tool write confirmation
  - pre-tool read allow
  - generic read allow
  - generic write confirmation
  - default allow
- Output must not include raw action, raw reason, shell command, file path, env/request string, secret, task goal, event payload, or user-provided input.
- Tool must be read-only: no durable event creation and no durable task/worker mutation.
- Register it with `ToolPermission(category="local", risk="read")`.
- Add focused unit tests in `tests/test_durable_workers.py` covering output shape, stable supported values, known rules, no-leak/read-only behavior, and compatibility with existing policy hook tools.
- Keep implementation narrow; do not change policy decisions unless a test exposes a clear existing bug.

## Tests

Run:

```text
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Boundaries

- Do not edit `agent_tasks/B_TASK.md` or `agent_tasks/B_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/A_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh A
```
