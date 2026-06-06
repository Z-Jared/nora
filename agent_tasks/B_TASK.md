# TASK-144: CLI slash surfaces v4 deterministic eval coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-143: CLI slash surfaces v4. Your job is deterministic offline eval coverage and test hardening after TASK-143 is visible in your worktree or after PM asks you to rebase/integrate.

Target UX:

- `/`, `/help`, `/wake`, `/model`, and `/workers` are short, monotone, plain-text slash surfaces.
- No section-heavy dashboard/panel style.
- No raw JSON.
- No model call or lifecycle feedback for slash commands.
- No API key/raw prompt/hidden reasoning/raw payload leak.
- Default CLI behavior from TASK-141/TASK-142 remains unchanged.

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
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic eval coverage for TASK-143 and update narrow CLI tests if needed.

Coverage requirements:

1. Slash launcher `/`
   - Includes required commands: `/wake`, `/setup`, `/model`, `/workers`, `/status`, `/test`, `/help`.
   - Output is compact and plain text.
   - No raw JSON, heavy panel markers, API key leak, hidden reasoning, or lifecycle lines.

2. `/help`
   - Is concise, not a long manual.
   - Preserves discoverability for project/git, model/setup, workers, memory/tasks/context, diagnostics.
   - No raw JSON or secret leak.

3. `/wake`
   - Provides bounded project snapshot: workspace, branch, git status summary, model/key state, knowledge files, tasks/workers.
   - Does not include `───` section headers or dashboard-like panels.
   - No raw file contents or secrets.

4. `/model`
   - Provides compact provider/model/base URL/API-key presence/enabled state.
   - Includes short recovery hints for missing key / 401 / model mismatch.
   - Does not print actual API key, raw `.env`, intelligence/speed/routing, or raw JSON.

5. `/workers`
   - Provides compact A/B summary with workspace/task/DONE status.
   - Missing `.ccb/` has one short recovery response.
   - Preserves ready-for-PM-review detection.
   - No raw worker report dump.

6. Compatibility
   - `/setup`, `/config`, `/doctor`, git/tool/durable commands still pass existing tests.
   - Slash commands do not call fake agent and do not emit `received`/`thinking`/`ready`.

## Scope

Primary files:

- `evals/run_evals.py`
- `tests/test_cli.py` only if necessary for focused CLI assertions
- `agent_tasks/B_DONE.md`

Do not edit:

- `mini_agent/cli.py` unless PM explicitly asks after reviewing TASK-143.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or broad substring-only pass conditions.
- Use tempdir-isolated roots and explicit settings/env/fake agent objects.
- Assert exact or meaningfully specific substrings.
- Assert secrets/API keys/raw prompts are not leaked.
- Do not call network, LLMs, external services, or CCB commands from evals.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-143 is not integrated into your worktree yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
