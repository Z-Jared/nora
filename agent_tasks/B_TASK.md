# TASK-140: CLI UI v2 deterministic eval coverage

You are Codex B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Codex A owns TASK-139: lightweight CLI UI v2 for Nora's default terminal surface. You own deterministic offline eval coverage after TASK-139 is integrated by Codex PM.

The intended CLI direction:
- Minimal `> ` prompt instead of `Nora(main)>`.
- Compact startup banner.
- Single subtle input status line: `model: ...   local-first   / for commands`.
- No intelligence/speed/routing in default status line; those belong in `/model`.
- No fullscreen TUI, no always-visible three-column dashboard.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md`
- `docs/knowledge/CHAT_INDEX.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/A_TASK.md`
- `mini_agent/cli.py`
- `tests/test_cli.py`
- `evals/run_evals.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic offline eval coverage for TASK-139 after PM integrates it.

Coverage requirements:

1. Minimal prompt
   - CLI prompt is exactly or effectively `> `.
   - Prompt output does not include `Nora(main)>`, branch, workspace, provider, or model.

2. Compact startup banner
   - Banner remains deterministic and contains required useful substrings:
     - `Nora 已启动`
     - `Workspace:`
     - `LLM:`
     - `Tools:`
     - `API key`
     - `/wake`, `/setup`, `/model`, `/workers`
   - Banner is compact and not a section-heavy dashboard.
   - No API key leak.

3. Input status line
   - Status line contains `model:`, current model or disabled state, `local-first`, and `/ for commands`.
   - Status line does not contain intelligence/speed/routing labels.
   - Status line does not leak API key, raw prompt, hidden reasoning, or raw payloads.

4. Lifecycle feedback
   - Normal prompt and multiline still emit deterministic lifecycle feedback.
   - Lifecycle output is compact.
   - Slash commands, blank input, and exit do not emit lifecycle noise.

5. Compatibility
   - `/`, `/setup`, `/model`, `/workers`, `/wake`, and `/help` remain plain text/Markdown, not raw JSON.
   - Existing CLI/provider/config evals continue to pass.

## Scope

Primary files:
- `evals/run_evals.py`
- `agent_tasks/B_DONE.md`

Only touch `tests/test_cli.py` if a tiny helper is absolutely needed.

Do not edit:
- `mini_agent/cli.py` unless PM explicitly asks after TASK-139 integration.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or broad substring-only pass conditions.
- Use tempdir-isolated roots and explicit settings/env objects where needed.
- Assert exact or meaningfully specific substrings.
- Assert secrets/API keys are not leaked.
- Do not call network, LLMs, external services, or CCB commands from evals.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-139 is not integrated yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening your scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
