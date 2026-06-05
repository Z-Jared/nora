# TASK-132: CLI setup/status UX deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-131 implementation for `/setup`/`/config` guidance and response status output. You own deterministic eval coverage for that user-facing CLI UX surface.

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

Add deterministic eval coverage for TASK-131:

1. `/setup` or `/config` guidance
   - Covers provider/model/base URL/key presence.
   - Covers provider-specific env keys for openai-compatible, anthropic, and gemini.
   - Verifies placeholder snippets do not leak real or fake secret values.
   - Verifies guidance for missing key / 401 / provider-model mismatch.

2. Response status output
   - Normal prompt emits deterministic status lines before and/or after `agent.run(...)`.
   - Slash commands do not emit model-call status lines.
   - Blank input and exit do not emit model-call status lines.
   - Status output does not reveal hidden reasoning or chain-of-thought.

3. Output structure and safety
   - Setup/config/status surfaces remain plain text/Markdown and not raw JSON.
   - No API key or secret leakage.
   - Evals remain offline and deterministic.

## Scope

Primary files:
- `evals/run_evals.py`
- `agent_tasks/B_DONE.md`

Only touch `tests/test_cli.py` if a very small focused helper is needed.

Avoid editing runtime implementation files. If TASK-131 surface is not yet present in your worktree, do not implement it yourself. Instead:
- Add coverage only where it can run against the current code without runtime changes, or
- Write `agent_tasks/B_DONE.md` with `Status: blocked/waiting for TASK-131 integration` and list the exact missing surface.

Do not edit:
- `mini_agent/cli.py` unless PM explicitly asks after TASK-131 integration.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or overly broad pass conditions.
- Use tempdir-isolated roots and explicit `env_path` where needed so local `.env` cannot affect evals.
- Assert exact or meaningfully specific substrings.
- Assert secrets/API keys are not leaked.
- Do not call network, LLMs, external services, or CCB commands from evals.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-131 is not integrated yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening your scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
