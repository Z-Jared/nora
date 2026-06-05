# TASK-134: CLI slash launcher/welcome deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-133 implementation for the `/` slash launcher/menu and startup welcome polish. You own deterministic offline eval coverage after TASK-133 is integrated by Codex PM.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
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

Add deterministic eval coverage for TASK-133 after PM integrates it:

1. Slash launcher/menu
   - Exact `/` returns a command launcher/menu.
   - Menu contains grouped start/project/worker/help commands.
   - Menu includes `/wake`, `/setup`, `/model`, `/workers`, `/status`, `/test`, and `/help`.
   - `/` does not trigger model-call status lines or model execution.
   - Output is plain text/Markdown, not raw JSON.

2. Startup welcome polish
   - Banner includes a next-action hint for `/`, `/wake`, and `/setup`.
   - Banner preserves workspace, branch when available, provider/model/key presence, tools count, active task summary, and worker summary.
   - Missing-key state is explicit and safe.
   - Configured-key state does not leak fake secrets.

3. Safety/structure
   - No chain-of-thought or hidden-reasoning markers.
   - No API key, token, `.env` secret, or raw JSON leakage.
   - Evals are offline, deterministic, tempdir-isolated, and do not call network/LLMs/CCB.

## Scope

Primary files:
- `evals/run_evals.py`
- `agent_tasks/B_DONE.md`

Only touch `tests/test_cli.py` if a tiny helper is absolutely needed.

Avoid editing runtime implementation files. If TASK-133 surface is not yet present in your worktree, do not implement it yourself. Instead write `agent_tasks/B_DONE.md` with `Status: blocked/waiting for TASK-133 integration` and list the exact missing surface.

Do not edit:
- `mini_agent/cli.py` unless PM explicitly asks after TASK-133 integration.
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

If TASK-133 is not integrated yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening your scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
