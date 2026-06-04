# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-102: Deterministic eval coverage for runtime policy hook evaluator v1

## Context

TASK-101 added a minimal read-only runtime policy evaluator tool:

```text
evaluate_runtime_policy_hook(hook, action="", category="", risk="", reason="")
```

It supports lifecycle hooks such as `pre_tool`, `pre_shell`, `pre_git`, `post_test`, `before_handoff`, and `before_commit`, and returns bounded decision metadata:

- `decision`: `allow`, `confirm`, or `block`
- `requires_confirmation`
- `blocked`
- `reason_label`
- `reason_present`
- `policy_version`
- `matched_rules`
- sanitized action fields (`action`, `action_label`, `action_present`)

Unit coverage exists in `tests/test_durable_workers.py`. The remaining gap is deterministic offline eval coverage in `evals/run_evals.py`.

## Goal

Add deterministic eval cases proving the runtime policy hook evaluator is auditable, bounded, no-leak, read-only, and compatible.

## Requirements

- Add focused eval coverage in `evals/run_evals.py`.
- Prefer small helper functions and isolated temp DB/workspace fixtures consistent with the existing durable-runtime eval style.
- Cover at least:
  1. Read/pre-tool decision:
     - `pre_tool` + `risk=read` returns `decision="allow"`, no confirmation, not blocked, and a safe matched rule.
  2. Write/high-risk confirmation:
     - `pre_tool` + `risk=write`, `pre_shell` or `pre_git` + `risk=write`, and/or `before_commit` + `risk=write/high` returns `decision="confirm"` with `requires_confirmation=True`.
  3. Block decisions:
     - `risk=destructive` and/or `risk=external_send` returns `decision="block"` and `blocked=True`.
  4. Bounded validation:
     - Unknown hook returns `error="unsupported_hook"` and does not echo the raw unknown hook sentinel.
     - Unknown category/risk normalize to `"unknown"` where applicable.
  5. Safety/no-leak:
     - Raw `reason` sentinel is not present in output.
     - Secret-like action (`SECRET_VALUE_XYZ` or similar), env-like action, shell command action, and workspace path action are redacted and not present in serialized output.
     - Safe short action label such as `read_file` is preserved.
  6. Read-only/no mutation:
     - Running the evaluator does not create durable events and does not mutate task/worker state.
  7. Compatibility:
     - Existing evals still pass.
     - `list_tool_permissions` includes `evaluate_runtime_policy_hook`.

## Tests

Run:

```text
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_workers.RuntimePolicyHookEvaluatorTests
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
git diff --check
```

## Boundaries

- Prefer eval-only changes in `evals/run_evals.py`.
- Do not modify runtime unless an eval exposes a real TASK-101 bug; if that happens, keep the runtime fix minimal and explain it in `B_DONE.md`.
- Do not edit `agent_tasks/A_TASK.md` or `agent_tasks/A_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/B_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh B
```

## Notes

- TASK-101 is committed on `main`.
- Keep eval assertions concrete; avoid evals that only assert tool existence.
- Keep outputs bounded and safe; do not store or assert raw task content, file contents, shell strings, env strings, workspace paths, or arbitrary unbounded input.
