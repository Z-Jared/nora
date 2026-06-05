# TASK-136: CLI terminal UI polish deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-135 implementation for terminal UI polish: startup landing panel, model-call lifecycle feedback, output formatting consistency, and clearer config/error recovery text. You own deterministic offline eval coverage after TASK-135 is integrated by Codex PM.

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

Add deterministic offline eval coverage for TASK-135 after PM integrates it:

1. Startup landing panel
   - Banner has clear deterministic sections for identity/status, workspace/branch, model/API-key state, and next actions.
   - Banner preserves existing workspace, model/provider, key presence, tools count, task/worker state when present.
   - Missing-key and configured-key states are safe and do not leak fake secrets.

2. Response lifecycle feedback
   - Normal prompt emits deterministic lifecycle feedback.
   - Multiline prompt emits deterministic lifecycle feedback.
   - Slash commands, blank input, and exit emit no model-call lifecycle noise.
   - Lifecycle output does not reveal hidden reasoning or chain-of-thought.

3. Output readability and recovery safety
   - `/`, `/setup`, `/model`, `/workers`, and `/help` remain plain text/Markdown and not raw JSON.
   - Config/error recovery output still includes useful exact guidance substrings: `/setup`, `API key`, `401 Unauthorized`, `provider/model 不匹配`.
   - No API key, token, `.env` secret, hidden reasoning, raw prompt, or raw tool payload leakage.

## Scope

Primary files:
- `evals/run_evals.py`
- `agent_tasks/B_DONE.md`

Only touch `tests/test_cli.py` if a tiny helper is absolutely needed.

Avoid editing runtime implementation files. If TASK-135 surface is not yet present in your worktree, do not implement it yourself. Instead write `agent_tasks/B_DONE.md` with `Status: blocked/waiting for TASK-135 integration` and list the exact missing surface.

Do not edit:
- `mini_agent/cli.py` unless PM explicitly asks after TASK-135 integration.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or overly broad pass conditions.
- Use tempdir-isolated roots and explicit `env_path` where needed so local `.env` cannot affect evals.
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

If TASK-135 is not integrated yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening your scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
