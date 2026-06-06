# TASK-145: Claude Code-like startup header and working indicator

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora's terminal UX is being tightened toward Claude Code-like restraint:

- Prompt is exactly `> `.
- Normal replies render without `Agent:`.
- Lifecycle feedback is `received`, `thinking`, `ready`.
- Input hint is a single line: `model: ... | local-first | / for commands`.
- Slash pages are now compact plain-text surfaces.

The next startup gap is the banner. The user provided a Claude Code screenshot where startup information sits beside a small pixel icon:

- left: small mascot/icon
- right: product name/version, model/effort/billing state, current path
- below: only short warnings when needed
- bottom: minimal prompt/input surface

For Nora, implement the same structure with a small robot ASCII icon and compact information next to it. Keep it monochrome/plain text and avoid a dashboard or welcome panel.

The user also wants Codex-like visibility while Nora is thinking/working. This must be a safe progress display only: show stages such as received/working/ready or bounded tool/action summaries, but never hidden reasoning, chain-of-thought, raw prompts, raw tool payloads, or secrets.

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

Replace the current startup `banner()` with a Claude Code-like startup header, and update ordinary model-call feedback to a Codex-like safe working indicator.

Required behavior:

1. Header layout
   - Use a small Nora robot ASCII icon on the left and information on the right.
   - Keep the header compact: target 3-6 non-empty lines, plus optional short warning lines.
   - The first information line must identify the product, e.g. `Nora Code`.
   - The next line should show model state: configured provider/model when enabled, or local/disabled state when not enabled.
   - Another line should show the current workspace path.
   - Information must visually sit beside the icon, not below a separate logo block.

2. Keep Claude-like restraint
   - Remove the old `Nora 已启动 — 本地优先，高风险工具会先确认。` welcome sentence.
   - Do not add section headers such as `Status`, `Workspace`, `Model`, `Tools`, `Next`.
   - Do not add `===`, `───`, boxed panels, tables, cards, or dashboard-style blocks.
   - Do not add color dependencies, curses, rich, textual, or fullscreen UI.

3. Preserve useful status
   - Preserve model/provider and API-key presence without printing secret values.
   - Preserve workspace path.
   - Preserve worker summary only if it can remain short; do not turn the startup header into `/workers`.
   - Preserve command discoverability as one short hint line if needed, but keep the bottom input area minimal.
   - Keep `_input_status_line()` behavior unless a focused test adjustment is necessary.

4. Safety and compatibility
   - Startup banner must not call the model.
   - Startup banner must not emit `received`, `thinking`, or `ready`.
   - No API key, token, `.env` value, raw prompt, hidden reasoning, raw tool payload, or raw file content leak.
   - Slash commands and existing CLI command semantics must continue working.

5. Codex-like working display
   - When a normal prompt or multiline prompt calls the agent/model, show a compact visible work state before the response, e.g. `• Working` or another short Claude/Codex-like line.
   - Preserve a clear completion state after the response if the current CLI contract expects one.
   - Do not show working status for slash commands, blank input, `exit`, or `quit`.
   - Do not reveal hidden reasoning, raw prompt text, raw model payloads, raw tool payloads, API keys, `.env` values, or private file contents.
   - Keep output deterministic for tests; do not implement live streaming unless it is already supported by existing abstractions.

## Scope

Primary files:

- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `evals/run_evals.py` unless a tiny unit-test helper absolutely requires it. Claude B owns TASK-146 eval coverage.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Non-Goals

- No animation in this task.
- No chain-of-thought or hidden reasoning display.
- No live streaming implementation unless it is a trivial wrapper around existing deterministic status output.
- No web UI redesign.
- No icon/favicon/package-data changes.
- No model routing behavior changes.
- No worker runtime behavior changes.
- No Git/tool/durable task command semantics changes.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If existing evals fail only because TASK-146 has not yet updated expected startup banner output, report the exact failing eval names and still make unit tests pass.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
