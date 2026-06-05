# TASK-135: CLI terminal UI polish v3

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora's CLI now has `/wake`, `/setup`, `/config`, `/model`, `/workers`, deterministic model-call status lines, a startup banner, and exact `/` command launcher. The user still feels the terminal UI is rough: replies appear abruptly, startup lacks a polished terminal landing surface, configuration/errors need clearer treatment, and the CLI should feel closer to Claude/Codex terminal ergonomics without adding a heavy TUI framework.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md`
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

Improve the terminal UI polish without changing backend runtime semantics:

1. Startup landing panel
   - Make `banner()` look like a compact terminal landing panel with clear sections:
     - identity/status
     - workspace/branch
     - model/API-key state
     - worker/task state if available
     - next actions
   - Keep it plain text/Markdown and deterministic.
   - Avoid noisy ASCII art or raw ANSI styling.
   - Keep all existing information and no secret leakage.

2. Response lifecycle feedback
   - Replace the current bare status lines with a small deterministic lifecycle:
     - user prompt accepted / model request started / response ready, or equivalent concise lines.
   - Normal prompt and multiline should show lifecycle feedback.
   - Slash commands, blank input, and exit must not show model-call lifecycle noise.
   - Do not reveal hidden reasoning or chain-of-thought.
   - Do not add streaming, async, curses, rich, textual, or other heavy dependencies.

3. Output readability helpers
   - Add small formatting helpers if useful, such as section headers/separators used consistently by banner, `/`, `/setup`, `/model`, `/workers`, and recovery hints.
   - Keep output compact and scannable on narrow terminals.
   - Avoid raw JSON for user-facing CLI surfaces except existing commands that intentionally inspect structured durable task/trace data.

4. Error/config recovery polish
   - Make provider/API-key/model mismatch recovery hints easier to scan.
   - Keep exact useful substrings already covered by tests/evals, including `/setup`, `API key`, `401 Unauthorized`, `provider/model 不匹配`, and no secret leak.

## Scope

Primary files:
- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:
- `evals/run_evals.py` — Codex B will own TASK-136 eval coverage after TASK-135 is integrated.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Non-Goals

- No web UI redesign.
- No curses/rich/textual/full-screen TUI.
- No model streaming transport.
- No backend runtime, scheduler, policy, worker, memory, or provider semantic changes.
- No hidden reasoning display.

## Safety Boundaries

- Never print API keys, tokens, `.env` values, private file contents, hidden reasoning, raw prompts, or raw tool payloads.
- Keep terminal UI deterministic for tests.
- Preserve existing slash command compatibility and prior CLI eval expectations.

## Durable Evidence

- Unit tests in `tests/test_cli.py`.
- Completion report in `agent_tasks/A_DONE.md`.
- No durable runtime event changes in this task.

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
