# TASK-154: TTY permissions selector and regression coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

The user reported three remaining real terminal UX gaps:

- `/` does not wake a command picker before Enter
- permissions still ask for manual `y/N` input instead of selectable options
- status/model information should live near the prompt, not as repeated printed footer text

Claude A owns TASK-153: the new TTY/raw terminal frontend. Your task is to make the behavior testable and cover the permission-selector side without bypassing safety.

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
- `agent_tasks/A_TASK.md`
- `mini_agent/app.py`
- `mini_agent/cli.py`
- `mini_agent/registry.py`
- `mini_agent/tools_common.py`
- `tests/test_cli.py`
- `evals/run_evals.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic coverage for Nora's TTY/raw terminal contract and, where the hook point is available, implement or integrate selectable permission confirmation.

Required coverage:

1. Mode selection
   - TTY mode chooses the interactive frontend.
   - non-TTY/redirected stdin chooses legacy `MiniAgentCLI`.
   - legacy pipes remain deterministic.

2. Slash command metadata
   - command completion source includes `/`, `/help`, `/wake`, `/model`, `/setup`, `/workers`, `/permissions`, `/doctor`, `/status`, `/test`, `/tools`, `/exit`
   - command descriptions are short and do not leak config/secrets

3. Permission UX
   - TTY permission prompt exposes selectable labels:
     - `Allow once`
     - `Deny`
     - optionally `Always allow this tool this session` if implemented
   - non-TTY fallback still supports existing `y/N` behavior
   - tests must prove denied approval still blocks the tool call
   - do not add auto-approval

4. Status/lifecycle
   - TTY mode does not append repeated model footer lines after every response
   - TTY thinking/status does not expose hidden reasoning or raw prompts
   - legacy non-TTY lifecycle remains compatible with existing evals unless PM integrates a deliberate contract update

5. Safety
   - no API key, raw `.env`, raw prompt status line, hidden reasoning marker, or raw JSON payload leaks in completion labels, toolbar/status helpers, permission prompts, or eval surfaces

## Scope

Primary files:

- `tests/test_cli.py`
- `evals/run_evals.py`
- `mini_agent/registry.py` / `mini_agent/tools_common.py` only if needed for a clean confirmation hook
- `mini_agent/interactive_cli.py` only if created by TASK-153 and you need narrow integration tests
- `agent_tasks/B_DONE.md`

Do not edit:

- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`

## Coordination

TASK-154 depends on TASK-153 for full green integration. If your worktree does not contain the interactive frontend yet:

- prepare tests/evals around stable helper APIs if possible
- avoid inventing a conflicting frontend
- clearly report any dependency/blocker in `agent_tasks/B_DONE.md`

If you can implement the permission selector independently, keep it behind an injectable confirmation function so Claude A's frontend can call it without changing backend permission semantics.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If full evals cannot pass because TASK-153 is not integrated in your worktree, run the most relevant targeted tests and report the dependency explicitly.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-153 was present in your worktree.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
