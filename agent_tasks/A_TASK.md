# TASK-147: Compact /model and /setup terminal surfaces v5

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora's default terminal surface is now intentionally close to Claude Code:

- startup header is compact and monochrome: Nora robot + `Nora Code` + model/API/path
- prompt is exactly `> `
- normal model calls show `Working...` then `Done.`
- slash commands stay compact and do not emit working status

The next UX gap is configuration surfaces. `/model` is close but still reads like a capitalized diagnostic block. `/setup` still starts with `=== Nora Setup / Config ===` and prints a large configuration wall. The user wants intelligence/speed/model details hidden behind `/model`, but that page should still feel like Claude Code: text-first, short, readable, no dashboard.

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

Make `/model` and `/setup` compact Claude Code-like terminal surfaces while preserving all useful recovery information.

Required behavior:

1. `/model`
   - Keep provider, model, base URL, API-key presence, timeout, and enabled state.
   - Prefer lowercase compact labels such as `provider:`, `model:`, `base URL:`, `API key:`, `timeout:`, `enabled:`.
   - Keep short recovery hints for missing key, missing provider, `401 Unauthorized`, and provider/model mismatch.
   - Preserve provider-specific env hints from `required_env_vars(...)` and `env_alternatives(...)`.
   - Do not include section bars, tables, boxes, or dashboard wording.

2. `/setup`
   - Remove `=== Nora Setup / Config ===`.
   - Keep enough setup guidance for openai-compatible, anthropic, and gemini users.
   - Keep common recovery hints, but shorten wording where possible.
   - It may be longer than `/model`, but should be visibly plain text and scannable.
   - Avoid standalone dashboard-like section headers. If grouping is needed, use short lowercase labels such as `current`, `env`, `recovery`.

3. Compatibility
   - `/model` and `/setup` must not call the model.
   - Slash commands, blank input, `exit`, and `quit` must not emit `Working...` or `Done.`
   - Keep `/config` as an alias for `/setup`.
   - Do not change provider loading, model routing, LLM calls, API key reading, or worker/runtime behavior.

4. Safety
   - Never print API key values, tokens, raw `.env`, raw prompt, hidden reasoning, raw tool payload, or raw file content.
   - Outputs must be deterministic, plain text, and ANSI-safe.

## Scope

Primary files:

- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `evals/run_evals.py` unless a tiny unit-test helper absolutely requires it. Claude B owns TASK-148 eval coverage.
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
- No model router behavior changes.
- No runtime/worker/plugin/tool semantic changes.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If existing evals fail only because TASK-148 has not yet updated expected `/model` or `/setup` output, report exact failing eval names and still make unit tests pass.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
