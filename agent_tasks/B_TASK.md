# TASK-148: /model and /setup compact surface deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-147: compact Claude Code-like `/model` and `/setup` surfaces. Nora's current default terminal direction is restrained and text-first:

- startup header is compact
- prompt is exactly `> `
- working indicator is `Working...` / `Done.`
- slash commands are plain text and do not call the model

Your job is deterministic offline eval coverage after TASK-147 is visible in your worktree or after PM asks you to rebase/integrate.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md`
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
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic eval coverage for TASK-147 and update narrow `/model`/`/setup` eval expectations.

Coverage requirements:

1. `/model` compact contract
   - Shows provider, model, base URL, API-key presence, timeout, and enabled state.
   - Keeps missing-key, missing-provider, 401, and provider/model mismatch recovery hints.
   - Keeps provider-specific env names and alternatives.
   - Does not include `===`, `───`, table/card/box/dashboard style, or raw JSON.

2. `/setup` compact contract
   - Keeps openai-compatible, anthropic, and gemini setup keys.
   - Keeps common recovery hints in bounded form.
   - No `=== Nora Setup / Config ===`.
   - No secret leak and no raw `.env` echo.

3. Slash compatibility
   - `/config` remains an alias for `/setup`.
   - `/model` and `/setup` do not call the fake agent.
   - `/model` and `/setup` do not emit `Working...` or `Done.`
   - Existing `/`, `/help`, `/wake`, `/workers` evals remain compatible.

4. Safety
   - No API key, token, raw prompt, hidden reasoning, raw tool payload, or raw file content leak.
   - No network, LLM, external service, or CCB command calls from evals.

## Scope

Primary files:

- `evals/run_evals.py`
- `tests/test_cli.py` only if necessary for focused startup/slash assertions
- `agent_tasks/B_DONE.md`

Do not edit:

- `mini_agent/cli.py` unless PM explicitly asks after reviewing TASK-147.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Coverage Quality Requirements

- No tautological assertions.
- Use tempdir-isolated roots and explicit settings/env/fake agent objects.
- Assert exact or meaningfully specific substrings.
- Assert secrets/API keys/raw prompts are not leaked.
- Keep evals deterministic/offline.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-147 is not integrated into your worktree yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
