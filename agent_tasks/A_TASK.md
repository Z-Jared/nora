# TASK-143: CLI slash surfaces v4

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora's default terminal surface is now intentionally minimal:

- Prompt is exactly `> `.
- Normal replies render without `Agent:`.
- Lifecycle feedback is `received`, `thinking`, `ready`.
- Input hint is a single line: `model: ... | local-first | / for commands`.

The next UX gap is slash pages. `/`, `/help`, `/wake`, `/model`, and `/workers` still feel more like panels/status dumps than Claude Code-like terminal command surfaces. The user wants the same restraint there: short, monochrome, plain text, functional.

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

Implement CLI slash surfaces v4. Keep behavior deterministic and narrow.

Required behavior:

1. `/` command palette becomes shorter
   - Keep required commands: `/wake`, `/setup`, `/model`, `/workers`, `/status`, `/test`, `/help`.
   - Prefer 4-6 compact groups max.
   - Avoid verbose descriptions, decorative section bars, raw JSON, and dashboard feel.
   - Keep it plain text and predictable.

2. `/help` becomes a concise index, not a long manual
   - It may list common commands and point to command-specific slash pages.
   - Preserve discoverability for existing command families: project/git, model/setup, workers, memory/tasks/context, diagnostics.
   - Do not remove command handling. Only reduce the default help text.

3. `/wake` becomes a short project snapshot
   - Remove `─── ... ───` section headers.
   - Keep useful facts: workspace, branch, git status summary, model/API-key state, knowledge file presence, active task summary, worker summary, recovery hints if needed.
   - Keep output bounded and readable.

4. `/model` becomes a compact config/status surface
   - Remove `=== Nora Model Configuration ===`.
   - Keep provider, model, base URL, API key presence, enabled state, and short recovery hints for missing key / 401 / model mismatch.
   - Never print actual API key or token values.
   - Do not expose intelligence/speed/routing in default slash output unless explicitly already part of model diagnostics.

5. `/workers` becomes a compact A/B worker summary
   - Remove `=== Nora Worker Status ===` and `--- claude-a ---` style panel sections.
   - Keep each worker on a small set of lines or a compact block: workspace present/missing, task file title, DONE status if present.
   - Preserve ready-for-PM-review detection.
   - Missing `.ccb/` should produce one short recovery line.

6. Compatibility and safety
   - `/setup`, `/config`, `/doctor`, git/tool/durable commands must continue working.
   - Slash commands must not call the model or emit lifecycle lines.
   - No raw JSON for `/`, `/help`, `/wake`, `/model`, `/workers`, `/setup`.
   - No API key, raw prompt, hidden reasoning, raw tool payload, or `.env` secret leak.

## Scope

Primary files:

- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `evals/run_evals.py` unless a tiny unit-test helper absolutely requires it. Claude B owns TASK-144 eval coverage.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Non-Goals

- No fullscreen TUI, curses, rich, textual, or fake fixed-bottom UI.
- No web UI redesign.
- No icon/favicon/package-data changes.
- No model routing behavior changes.
- No worker runtime behavior changes.
- No Git/tool/durable task command semantics changes.

## Safety Boundaries

- Never print API keys, tokens, `.env` values, private file contents, raw prompts, hidden reasoning, or raw tool payloads.
- Keep CLI output deterministic for tests/evals.
- Preserve slash command compatibility.
- Do not revert unrelated user/Codex work.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If existing evals fail only because TASK-144 has not yet updated expected CLI v4 slash output, report the exact failing eval names and still make unit tests pass.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
