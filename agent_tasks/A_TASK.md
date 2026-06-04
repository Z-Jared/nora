# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-101: Runtime policy hook evaluator v1

## Context

Recent work completed scheduler retry planning/execution/event metadata and deterministic eval coverage. The next north-star priority is the hook/policy kernel:

- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 9: lifecycle hooks for `pre-tool`, `post-tool`, `pre-edit`, `post-edit`, `pre-shell`, `pre-git`, `pre-plugin-call`, `post-test`, `before-handoff`, `before-commit`, `compact`, `stop`, and recovery events.
- Hooks should become policy-backed, testable, and traceable runtime mechanisms rather than prompt-only conventions.

This task is the smallest runtime foundation: add a read-only policy hook evaluator that returns safe decision metadata. Do not wire it into enforcement yet.

## Goal

Add a minimal, deterministic, read-only runtime policy evaluator tool that can answer:

> At this lifecycle hook, for this action/tool category/risk, what would runtime policy decide?

The output should be bounded, safe, and ready for future enforcement and event tracing.

## Requirements

- Add a registry tool such as `evaluate_runtime_policy_hook(...)` or an equivalent name consistent with local style.
- The tool must be read-only: no durable state mutation, no filesystem writes, no tool execution, no shell/git/browser/network/plugin calls.
- Inputs should support at least:
  - `hook`: lifecycle point, with support for at least `pre_tool`, `pre_shell`, `pre_git`, `before_commit`, `post_test`, `before_handoff`.
  - `action`: optional short action/tool name.
  - `category`: optional permission/category label such as `task`, `shell`, `git`, `file`, `network`, `plugin`, `model`, `test`.
  - `risk`: optional risk label such as `read`, `write`, `destructive`, `external_send`, `high`.
  - `reason`: optional human reason string, but do not echo raw reason text in output.
- Return a bounded JSON object with safe fields such as:
  - `hook`
  - `action`
  - `category`
  - `risk`
  - `decision`: one of `allow`, `confirm`, `block`
  - `requires_confirmation`: bool
  - `blocked`: bool
  - `reason_label`: bounded label, not raw user text
  - `reason_present`: bool
  - `policy_version`
  - `matched_rules`: bounded list of safe rule labels
- Initial policy can be simple and conservative:
  - read-like actions generally `allow`
  - write/high-risk/destructive/external-send actions generally `confirm`
  - unsupported/unknown hooks or clearly destructive git/shell categories can `block` or return bounded validation errors, whichever fits current style best
  - `before_commit` should require confirmation for write/high-risk commit-like actions
- Output must not leak raw `reason`, prompts, shell command strings, env/request strings, file contents, workspace paths, secrets, or arbitrary unbounded inputs.
- Keep implementation small and local to the registry/toolkit area that already handles permissions if possible.
- Add focused unit tests in `tests/test_durable_workers.py` or a more appropriate existing test file.

## Tests

Add tests covering at least:

- Known read/pre_tool policy returns `allow` and no confirmation.
- Known write/pre_tool or before_commit policy returns `confirm` / `requires_confirmation=True`.
- Clearly destructive shell/git/high-risk action returns `block` or `confirm` according to your chosen conservative policy, with safe `reason_label`.
- Unknown/bad hook validation is bounded and deterministic.
- `reason_present=True` when reason is passed, but raw reason sentinel is not present in output.
- Safety/no-leak for shell/env/request/workspace/secret-like sentinels.
- Read-only/no mutation: durable task/worker/event state counts are unchanged by evaluation.
- Compatibility: existing registry permission/approval behavior still works.

Run:

```text
python3 -m unittest tests.test_durable_workers
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Boundaries

- Do not enforce the policy yet; this is evaluator/scaffold only.
- Do not alter existing confirmation behavior unless a test exposes a real compatibility bug.
- Do not edit `agent_tasks/B_TASK.md` or `agent_tasks/B_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/A_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh A
```

## Notes

- Keep the public API additive and bounded.
- Prefer rule labels over raw input echoing.
- This task should make future policy enforcement easier, but it should not attempt to build the whole hook kernel in one pass.
