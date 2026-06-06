# TASK-153: Nora TTY raw terminal interaction layer v1

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

The recent CLI UX work only polished printed output. The user has now explicitly asked for the real terminal interaction layer:

- input should behave like Claude Code/Codex and stay owned by the bottom prompt area in manual TTY use
- typing `/` should open commands before pressing Enter
- command options must support up/down selection and Tab completion
- model/cwd/status belongs near the prompt, not printed after every reply
- thinking/status should be visible while the model works, without exposing hidden reasoning
- non-TTY scripts and tests must keep the existing `input()`/`print()` path

Pencil design reference:

- File: `pencil-new.pen`
- Node: `kdiWB`
- Name: `Nora CLI TUI Raw Terminal Mock v2`

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md`
- `docs/knowledge/CHAT_INDEX.md`
- `agent_tasks/BACKLOG.md`
- `mini_agent/app.py`
- `mini_agent/cli.py`
- `mini_agent/registry.py`
- `pyproject.toml`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Add a first real TTY/raw terminal frontend layer for manual `nora` sessions.

Expected architecture:

- Keep `MiniAgentCLI` as the legacy non-TTY fallback and as the core slash-command handler.
- Add a new focused module, likely `mini_agent/interactive_cli.py`.
- In `mini_agent/app.py`, choose:
  - TTY stdin/stdout: new interactive frontend
  - non-TTY, redirected stdin, tests, pipes: existing `MiniAgentCLI.run()`
- Use `prompt_toolkit` or an equivalent small terminal library if needed. If you add a dependency, update both `pyproject.toml` and `setup.py` if setup metadata requires it.

Required TTY behavior:

1. Prompt and toolbar
   - prompt text stays visually minimal: `> `
   - bottom toolbar shows compact status such as model/cwd/local-first
   - toolbar/status is not appended to chat history after every response

2. Slash command launcher
   - typing `/` opens command completions before Enter
   - command list should come from one registry/helper, not hard-coded in multiple unrelated places
   - include at least `/`, `/help`, `/wake`, `/model`, `/setup`, `/workers`, `/permissions`, `/doctor`, `/status`, `/test`, `/tools`, `/exit`
   - up/down selection and Tab completion should work through the terminal library

3. Thinking/status
   - while `agent.run(...)` is executing, show a compact transient status such as `Working...` or `Thinking...`
   - do not print repeated lifecycle noise into the transcript in TTY mode
   - do not expose hidden reasoning, raw prompts, raw tool payloads, or secrets

4. Fallback compatibility
   - `printf '/model\nexit\n' | nora` must still use the existing legacy CLI path
   - existing CLI unit tests that instantiate `MiniAgentCLI` should keep working
   - do not remove `Working...` / `Done.` from legacy non-TTY behavior unless tests are intentionally updated by PM

## Scope

Primary files:

- `mini_agent/interactive_cli.py` or similarly named new module
- `mini_agent/app.py`
- `mini_agent/cli.py` only for reusable slash command metadata/helpers
- `pyproject.toml`
- `setup.py` if dependency metadata exists there
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`

## Non-Goals

- No fullscreen dashboard.
- No curses-style custom renderer if a lighter prompt-session approach works.
- No Web UI changes.
- No model provider/router semantic changes.
- No hidden reasoning display.
- No auto-approval of tools.
- No broad rewrite of `MiniAgentCLI`.

## Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If feasible, also run a manual TTY smoke:

```bash
nora
```

Check `/` completion, arrow navigation, Tab completion, normal chat status, and `/exit`.

If the local installed `nora` is stale, report the exact install command needed instead of silently assuming success.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and any manual TTY observations.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
