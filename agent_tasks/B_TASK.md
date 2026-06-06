# TASK-150: Error recovery and doctor deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-149: compact Claude Code-like recovery, unknown slash, and `/doctor` surfaces. Current default terminal direction:

- startup header is compact
- prompt is exactly `> `
- working indicator is `Working...` / `Done.`
- `/model` and `/setup` are compact plain-text surfaces

Your job is deterministic offline eval coverage after TASK-149 is visible in your worktree or after PM asks you to rebase/integrate.

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

Add deterministic eval coverage for TASK-149 and update narrow recovery/doctor eval expectations.

Coverage requirements:

1. Recovery hints
   - 401, 403, missing key, timeout, model not found, unsupported provider, rate limit, quota/billing, and port-in-use each produce a short practical hint.
   - No old Chinese long hints and no `提示:`.
   - No raw error echo, raw prompt, or secret leak.

2. Unknown slash
   - Gives short `/` or `/help` guidance.
   - No old Chinese `输入 / 查看命令菜单`.
   - Does not call fake agent and does not emit `Working...` / `Done.`

3. `/doctor`
   - Shows workspace, git, llm, tools, data path, logs path, nora command.
   - Keeps provider-specific env hints for disabled LLM.
   - Uses compact English suggestions.
   - No secret leak, no raw `.env`, no section bars or dashboard formatting.
   - Does not call fake agent and does not emit `Working...` / `Done.`

## Scope

Primary files:

- `evals/run_evals.py`
- `tests/test_cli.py` only if necessary for focused recovery/doctor assertions
- `agent_tasks/B_DONE.md`

Do not edit:

- `mini_agent/cli.py` unless PM explicitly asks after reviewing TASK-149.
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

If TASK-149 is not integrated into your worktree yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
