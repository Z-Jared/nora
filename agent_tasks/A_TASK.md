# TASK-129: CLI wake/setup/status UX v1

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora is shifting this iteration from backend runtime accumulation to CLI front-end usability. The goal is to make the CLI feel like a daily project workbench rather than a bag of scripts.

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

Improve CLI wake/setup/status UX v1:

1. `/wake`
   - Read project context from `docs/knowledge/PROJECT_WAKEUP.md`, `docs/knowledge/DECISIONS.md`, `docs/knowledge/CHAT_INDEX.md`, `AGENTS.md`, git status, and `agent_tasks/BACKLOG.md`.
   - Output a concise project wake panel suitable for a fresh CLI session.
   - If files are missing or the user starts outside a Nora project, return clear recovery guidance.

2. Startup page
   - On CLI start, show workspace, branch, provider/model, whether required key material appears configured, current task/backlog summary, worker state summary if available, and common commands.
   - Keep output compact and deterministic for tests.

3. `/model`
   - Show current provider/model/base URL/key presence without leaking key values.
   - Diagnose missing provider/model/key and give concrete next steps.
   - `/setup` can remain future work, but help text should point to it as upcoming or provide config-file/env guidance.

4. `/workers`
   - Show Claude A/B / CCB worker status from project files where available.
   - Include current tasks and whether A_DONE/B_DONE appear ready for PM review.
   - Handle missing `.ccb` or task files gracefully.

5. Error recovery hints
   - Add user-readable suggestions for common provider/config failures such as 401/unauthorized, missing `.env`, missing API key, port already in use, unsupported provider, and provider/model mismatch.
   - Do not leak secrets.

## Scope

Primary files:
- `mini_agent/cli.py`
- `tests/test_cli.py`

Possible supporting files only if needed:
- `mini_agent/config.py`
- `mini_agent/settings.py`
- `agent_tasks/A_DONE.md`

Do not edit:
- `evals/run_evals.py` — Claude B owns TASK-130 smoke/eval coverage.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## UX Constraints

- Keep CLI output readable in a terminal.
- Prefer Markdown-ish plain text sections.
- Never print raw API keys, tokens, `.env` values, full secrets, or private file contents.
- Keep behavior deterministic and offline for tests.
- Do not add a heavy dependency or framework.
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
