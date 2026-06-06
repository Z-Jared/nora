# TASK-146: Startup header deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-145: a Claude Code-like startup header with a small Nora robot ASCII icon on the left and compact status text on the right. Your job is deterministic offline eval coverage after TASK-145 is visible in your worktree or after PM asks you to rebase/integrate.

Target UX:

- Startup header resembles Claude Code's compact first screen: small icon left, product/model/path right.
- Product line includes `Nora Code`.
- Model line shows provider/model when configured or local/disabled state when not configured.
- Workspace path is visible.
- No old Chinese welcome sentence, no dashboard panel, no section-heavy banner.
- Prompt remains `> ` and input status remains compact.

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

Add deterministic eval coverage for TASK-145 and update narrow startup-banner eval expectations.

Coverage requirements:

1. Claude-like startup header shape
   - Banner includes `Nora Code`.
   - Banner includes a small robot/icon marker on the left side of the first few lines.
   - Banner includes model state and workspace path.
   - Header is compact and bounded, not a long welcome panel.

2. Old banner regression guards
   - No `Nora 已启动`.
   - No section headers such as `Status`, `Workspace`, `Model`, `Tools`, `Next` as standalone panel sections.
   - No `===`, `───`, boxed-panel/table/card style.
   - No verbose command menu inside startup banner.

3. Configured and disabled model states
   - Configured provider/model appears without leaking actual API key.
   - Disabled/local state remains understandable and short.
   - Missing key / API-key presence is represented safely.

4. Worker summary and compatibility
   - Existing `.ccb` DONE summary coverage should still pass or be updated to the new compact wording.
   - Prompt remains exactly `> `.
   - Startup banner does not call fake agent and does not emit `received`/`thinking`/`ready`.
   - Slash command evals remain compatible.

5. Safety
   - No API key, raw `.env`, raw prompt, hidden reasoning, raw tool payload, or raw file content leak.
   - No network, LLM, external service, or CCB command calls from evals.

## Scope

Primary files:

- `evals/run_evals.py`
- `tests/test_cli.py` only if necessary for focused startup assertions
- `agent_tasks/B_DONE.md`

Do not edit:

- `mini_agent/cli.py` unless PM explicitly asks after reviewing TASK-145.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or broad substring-only pass conditions.
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

If TASK-145 is not integrated into your worktree yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
