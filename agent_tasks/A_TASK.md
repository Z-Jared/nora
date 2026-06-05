# TASK-133: CLI slash launcher and welcome polish v2

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora now has `/wake`, `/setup`, `/config`, `/model`, `/workers`, startup worker status, and deterministic model-call status lines. The next user-facing gap is CLI discoverability: typing `/` should open a usable command launcher/menu instead of feeling broken, and the startup/welcome text should feel more intentional without adding a full terminal UI framework.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/CHAT_INDEX.md`
- `agent_tasks/BACKLOG.md`
- `mini_agent/cli.py`
- `tests/test_cli.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Implement CLI UX v2 focused on slash discoverability and welcome polish:

1. Slash launcher
   - When the user enters exactly `/`, return a concise command launcher/menu.
   - The menu should group common commands by purpose, such as:
     - Start: `/wake`, `/setup`, `/model`
     - Project: `/status`, `/diff`, `/test`
     - Workers: `/workers`
     - Memory/tasks/context: existing relevant commands if already supported
     - Help: `/help`
   - Include one-line descriptions. Keep it plain text/Markdown and deterministic.
   - Do not execute a model call for `/`.
   - Do not emit model-call status lines for `/`.
   - Do not print raw JSON.

2. Startup welcome polish
   - Improve `banner()` so a new terminal starts with a clearer, more useful landing panel.
   - Keep existing key information: workspace, branch, LLM/provider/model, API-key presence, tool count, active tasks, worker summary, common commands.
   - Add a short “next action” hint that points users to `/`, `/wake`, and `/setup`.
   - Make missing API-key state easy to understand without leaking secrets.
   - Keep output deterministic and friendly in plain terminal text.

3. Prompt/status polish
   - Keep the existing prompt shape compatible.
   - If you adjust wording of status lines, preserve deterministic started/completed semantics and update tests.
   - Do not add streaming, async, curses/rich/textual dependencies, or hidden reasoning output.

## Scope

Primary files:
- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:
- `evals/run_evals.py` — Codex B will own TASK-134 eval coverage after TASK-133 is integrated.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## UX Constraints

- Never print API keys, tokens, `.env` values, full secrets, private file contents, or hidden reasoning.
- Do not add raw ANSI art that may look noisy in logs. Simple ASCII separators are okay.
- Keep terminal output compact enough for small screens.
- Preserve existing command compatibility.
- Do not broaden backend runtime behavior.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
