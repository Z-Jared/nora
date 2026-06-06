# TASK-141: CLI default terminal surface v3

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

The user wants Nora's terminal page redesigned toward Codex/Claude Code restraint. TASK-139/TASK-140 already moved Nora to a minimal `> ` prompt, compact banner, and a single model/local-first command hint. The next step is another reduction pass:

- Default interaction should feel like a quiet terminal assistant, not a dashboard.
- Keep `> ` as the only input prompt.
- Keep replies above the prompt.
- Avoid heavy separator/footer chrome around every turn.
- Avoid `Agent:` labels in normal model replies unless needed for compatibility.
- Keep intelligence/speed/routing hidden under `/model`, not in default prompt/status.
- Keep workers/tasks/traces on slash commands, not as always-visible panels.

Current PM state:

- Main branch is at or after `8b87512 Polish CLI input footer`.
- Claude A/B worktrees were fast-forwarded to main after old TASK-139/140 residue was stashed.
- The main repository currently has unrelated icon/favicon edits. Do not touch those files.

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

Implement CLI terminal surface v3 in the existing plain terminal CLI.

Required behavior:

1. Default prompt remains minimal
   - `MiniAgentCLI.prompt()` must remain exactly `> `.
   - No branch, workspace, provider, model, or tool count in the prompt.

2. Replace heavy input footer with a quiet one-line hint
   - The current repeated 52-character separator footer is still too visually heavy.
   - Replace it with a one-line status/hint such as `model: <model-or-disabled> | local-first | / for commands`.
   - Do not print decorative separator bars around every turn.
   - It is acceptable to print the one-line hint after banner and after normal responses, but keep output deterministic.

3. Remove normal `Agent:` response label
   - A one-line model response should render as the response text itself, not `Agent: <text>`.
   - Multiline model responses should preserve text exactly enough for tests, without adding a speaker label.
   - Do not expose hidden reasoning or raw tool payloads.

4. Compact lifecycle feedback
   - Replace verbose lifecycle lines with compact deterministic lines close to:
     - `received`
     - `thinking`
     - `ready`
   - ASCII is preferred for this task to avoid terminal/font noise.
   - Slash commands, blank input, and exit must not emit lifecycle lines.
   - Keep lifecycle output free of raw prompt, API key, hidden reasoning, or raw payload.

5. Banner stays compact and useful
   - Keep required useful substrings: `Nora 已启动`, `Workspace:`, `LLM:`, `Tools:`, `API key`, `/wake`, `/setup`, `/model`, `/workers`.
   - Do not reintroduce section-heavy panels, dashboard columns, or long always-visible task/worker blocks.
   - A single concise worker summary line is acceptable if already present.

6. Slash commands remain stable
   - `/`, `/setup`, `/model`, `/workers`, `/wake`, `/help` must remain plain text/Markdown, not raw JSON.
   - Do not change runtime behavior for tools, model routing, worker status, durable tasks, or web UI.

## Scope

Primary files:

- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `evals/run_evals.py` unless a tiny unit-test helper absolutely requires it. Claude B owns TASK-142 eval coverage.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/index.html`
- `mini_agent/static/favicon.svg`
- `pyproject.toml`
- `setup.py`

## Non-Goals

- No curses/rich/textual/fullscreen TUI.
- No fake fixed-bottom input box.
- No web UI redesign.
- No model routing behavior changes.
- No intelligence/speed/routing default status display.
- No hidden reasoning display.
- No icon/favicon/package-data changes.

## Safety Boundaries

- Never print API keys, tokens, `.env` values, private file contents, raw prompts, hidden reasoning, or raw tool payloads.
- Keep CLI output deterministic for tests/evals.
- Preserve slash command compatibility.
- Do not revert unrelated user/Codex icon work in the main repository.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If existing evals fail only because TASK-142 has not yet updated expected CLI v3 output, report the exact failing eval names and still make unit tests pass.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
