# TASK-149: Compact error recovery and doctor surfaces v6

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora's terminal UI has been tightened toward Claude Code-like restraint:

- startup header is compact and monochrome
- prompt is exactly `> `
- normal model calls show `Working...` then `Done.`
- `/model` and `/setup` are compact plain-text configuration surfaces

The next inconsistency is error/recovery text. `_error_recovery_hint()` still returns long Chinese `提示:` lines, unknown slash still returns Chinese menu guidance, and `/doctor` suggestions mix English labels with long Chinese sentences. These are user-visible terminal surfaces, so they should match the compact style.

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
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Make error recovery, unknown slash, and `/doctor` outputs compact Claude Code-like terminal surfaces.

Required behavior:

1. Error recovery hints
   - Replace long Chinese `提示:` strings with short English hints.
   - Preserve detection for 401/unauthorized, 403/forbidden, missing API key, port in use, connection/timeout, model not found, unsupported provider, rate limit, quota/billing.
   - Keep hints practical and short, e.g. `hint: check API key in .env`.
   - Never echo raw error text inside the hint.

2. Unknown slash command
   - Keep it short and plain text.
   - Remove Chinese `输入 / 查看命令菜单...`.
   - Preserve guidance to use `/` or `/help`.

3. `/doctor`
   - Keep `Nora doctor`, workspace, git, llm, tools, data path, logs path, nora command.
   - Convert suggestions to short English bullets.
   - Preserve provider-specific env hints from `required_env_vars(...)` and `env_alternatives(...)`.
   - Do not print API key values or raw `.env` contents.
   - Keep lowercase/plain labels where practical; no tables, boxes, `===`, or section bars.

4. Compatibility
   - `/doctor`, unknown slash, and recovery hint paths must not call the model.
   - Slash commands, blank input, `exit`, and `quit` must not emit `Working...` or `Done.`
   - Do not change model calls, provider loading, model routing, tools, worker/runtime behavior, or Web UI.

## Scope

Primary files:

- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `evals/run_evals.py` unless a tiny unit-test helper absolutely requires it. Claude B owns TASK-150 eval coverage.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Non-Goals

- No fullscreen TUI, animation, streaming, colors, rich/textual/curses dependency, or UI framework.
- No hidden reasoning display.
- No Web UI redesign.
- No model router/provider behavior changes.
- No runtime/worker/plugin/tool semantic changes.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If existing evals fail only because TASK-150 has not yet updated expected recovery/doctor output, report exact failing eval names and still make unit tests pass.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
