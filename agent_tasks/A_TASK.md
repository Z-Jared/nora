# TASK-139: CLI UI v2 lightweight terminal surface

You are Codex A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

The user wants Nora's default CLI to feel closer to modern terminal coding assistants like Claude Code and Codex, but **not** a complex dashboard. The agreed direction:

- Default prompt should be `>` rather than `Nora(main)>`.
- Agent replies stay above the input prompt.
- The default CLI remains plain terminal output, not fullscreen TUI.
- A subtle status line near the input should show only model/local-first/command hint.
- Intelligence/speed/routing controls stay inside `/model`, not in the default prompt/status line.
- Workers/tasks/trace/permissions stay on slash commands, not as always-visible side panels.

Reference image generated during PM discussion:
- `/Users/mac/.codex/generated_images/019e77d1-89fc-7b61-955e-257bc11c0091/ig_09ae02644c868c6b016a2302d28dcc8197935c3a503026ea8d.png`

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

Implement a lightweight CLI UI v2 in the existing plain terminal CLI.

Required behavior:

1. Minimal prompt
   - Replace `Nora(main)> ` / `Nora> ` prompt with a minimal `> ` prompt.
   - Branch/workspace/model must not be repeated in every input prompt.
   - Multiline continuation may remain `... ` unless you can improve it safely.

2. Compact startup banner
   - Reduce startup banner from section-heavy panel to a compact 8-12 line startup surface.
   - Keep exact useful substrings required by existing tests/evals where practical: `Nora 已启动`, `Workspace:`, `LLM:`, `Tools:`, `API key`, `/wake`, `/setup`, `/model`, `/workers`.
   - Show workspace, branch if available, model/provider, API-key presence, tools count, and next-action hint.
   - Avoid always-visible task/worker/check panels in default banner unless one concise line is enough.

3. Lightweight input status line
   - Add a helper such as `_input_status_line()` that returns a single subtle line containing:
     - `model: <model-or-disabled>`
     - `local-first`
     - `/ for commands`
   - Do not show intelligence/speed/routing in the default status line.
   - Make this line available near input in plain CLI by printing it after the banner and after each agent response, or by including it in a compact footer. Keep deterministic tests possible.

4. Quieter lifecycle feedback
   - Keep deterministic lifecycle feedback, but make it less noisy and closer to:
     - `✓ received`
     - `⏳ thinking`
     - `✓ ready`
   - It is acceptable to retain Chinese if tests require it, but the UI should feel compact.
   - Slash commands, blank input, and exit must not emit lifecycle noise.
   - No hidden reasoning or chain-of-thought.

5. Slash command/menu alignment
   - Keep exact `/` launcher behavior.
   - Optionally tighten labels so the menu feels like a command palette, but do not make a fullscreen TUI.

## Scope

Primary files:
- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:
- `evals/run_evals.py` — Codex B owns TASK-140 eval coverage after TASK-139 is integrated.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Non-Goals

- No curses/rich/textual/fullscreen TUI.
- No actual fixed-bottom input box; plain CLI cannot guarantee that without TUI.
- No web UI redesign.
- No model routing behavior changes.
- No intelligence/speed default status display.
- No hidden reasoning display.

## Safety Boundaries

- Never print API keys, tokens, `.env` values, private file contents, raw prompts, hidden reasoning, or raw tool payloads.
- Keep CLI output deterministic for tests/evals.
- Preserve slash command compatibility.

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
