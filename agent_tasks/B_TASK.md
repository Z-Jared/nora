# TASK-130: CLI UX smoke/eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

This iteration shifts Nora from backend runtime accumulation to CLI front-end usability. Claude A owns TASK-129 implementation. You own deterministic smoke/eval coverage for that CLI UX surface.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/CHAT_INDEX.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/A_TASK.md`
- `mini_agent/cli.py`
- `tests/test_cli.py`
- `evals/run_evals.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic CLI UX smoke/eval coverage for the new user-facing CLI workbench surfaces:

1. no-model / missing-key startup diagnostics
2. configured provider/model startup diagnostics without leaking keys
3. bad/unauthorized key error recovery hint
4. non-project directory startup or `/wake` recovery guidance
5. `/wake` project panel content
6. `/model` provider/model/key-safe diagnostics
7. `/workers` CCB A/B/task/DONE status summary
8. Markdown/plain-text structure for CLI output

## Scope

Primary files:
- `evals/run_evals.py`
- `tests/test_cli.py` only if focused unit coverage is needed
- `agent_tasks/B_DONE.md`

Avoid editing runtime implementation files. If TASK-129 surface is not yet present in your worktree, do not implement it yourself. Instead:
- Add coverage only where it can run against the current code without runtime changes, or
- Write `agent_tasks/B_DONE.md` with `Status: blocked/waiting for TASK-129 integration` and list the exact missing surface.

Do not edit:
- `mini_agent/cli.py` unless PM explicitly asks after TASK-129 integration.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or overly broad pass conditions.
- Evals must be deterministic and offline.
- Use tempdir-isolated project roots when simulating project/non-project startup.
- Assert exact or meaningfully specific substrings for `/wake`, `/model`, `/workers`, startup page, and recovery hints.
- Assert secrets/API keys are not leaked.
- Do not call network, LLMs, external services, or CCB commands from evals.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-129 is not integrated yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening your scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
