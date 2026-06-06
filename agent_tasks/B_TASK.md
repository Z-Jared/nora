# TASK-142: CLI default terminal surface v3 deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-141: CLI default terminal surface v3. Your job is deterministic offline eval coverage and test hardening for the same UX direction after TASK-141 is visible in your worktree or after PM asks you to rebase/integrate.

Target UX:

- Default prompt is exactly `> `.
- Default output uses a quiet one-line hint, not heavy separator bars around every turn.
- Normal model replies do not get an `Agent:` label.
- Lifecycle feedback is compact and deterministic: `received`, `thinking`, `ready` style.
- No intelligence/speed/routing in the default status/hint; those remain under `/model`.
- Slash commands remain plain text/Markdown.

Current PM state:

- Main branch is at or after `8b87512 Polish CLI input footer`.
- Old TASK-139/140 residue in CCB worktrees was stashed before this task.
- The main repository currently has unrelated icon/favicon edits. Do not touch those files.

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

Add deterministic eval coverage for TASK-141 and update narrow CLI tests if needed.

Coverage requirements:

1. Minimal prompt
   - Prompt is exactly `> `.
   - Prompt output does not include branch, workspace, provider, model, tools, or `Nora(main)>`.

2. Quiet input hint
   - Default run output contains a one-line `model:` / `local-first` / `/ for commands` hint.
   - Default run output does not contain repeated decorative separator bars such as long runs of `─` around the prompt area.
   - Hint does not contain intelligence/speed/routing labels.

3. Unlabeled model replies
   - Normal one-line fake model response appears without an `Agent:` prefix.
   - Multiline fake model response remains readable and is not wrapped in raw JSON.

4. Compact lifecycle
   - Normal prompt and multiline emit deterministic compact lifecycle feedback.
   - Slash commands, blank input, and exit do not emit lifecycle feedback.
   - Lifecycle output does not leak raw prompt, API key, hidden reasoning, shell command, raw JSON, or raw payload.

5. Compatibility
   - `/`, `/setup`, `/model`, `/workers`, `/wake`, and `/help` remain plain text/Markdown.
   - Existing provider/config/no-secret evals continue to pass.

## Scope

Primary files:

- `evals/run_evals.py`
- `tests/test_cli.py` only if necessary for focused CLI assertions
- `agent_tasks/B_DONE.md`

Do not edit:

- `mini_agent/cli.py` unless PM explicitly asks after reviewing TASK-141.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/index.html`
- `mini_agent/static/favicon.svg`
- `pyproject.toml`
- `setup.py`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or broad substring-only pass conditions.
- Use tempdir-isolated roots and explicit settings/env/fake agent objects.
- Assert exact or meaningfully specific substrings.
- Assert secrets/API keys/raw prompts are not leaked.
- Do not call network, LLMs, external services, or CCB commands from evals.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-141 is not integrated into your worktree yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
