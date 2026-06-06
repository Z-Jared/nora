# TASK-152: Final terminal UX regression eval sweep

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Claude A owns TASK-151: the final copy consistency sweep for Nora's CLI terminal redesign. Your job is to add deterministic regression evals that lock the final terminal UX contract.

Current target:

- startup header compact, no old welcome/panel
- prompt exactly `> `
- normal/multiline model calls emit `Working...` / `Done.`
- slash commands do not emit lifecycle noise
- `/model`, `/setup`, recovery, unknown slash, `/doctor`, `/wake`, `/help`, `/workers` are compact plain text
- no secret/raw prompt/hidden reasoning leak

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

Add a final deterministic terminal UX regression eval suite.

Coverage requirements:

1. Global surface scan
   - Build representative outputs for startup, `/`, `/help`, `/wake`, `/model`, `/setup`, `/workers`, `/doctor`, unknown slash, normal prompt, multiline prompt.
   - Assert no old panel markers: `===`, `───`, boxed/table/card markers.
   - Assert no old CLI copy: `Nora 已启动`, `提示:`, `未知命令`, `输入 / 查看命令菜单`, `Provider:`, `Model:`, `Base URL:`, `Timeout:`, `Enabled:`, `Agent:`.
   - Allow intentional `Workspace:`/`Branch:` in `/wake` only if still present.

2. Lifecycle contract
   - Normal and multiline prompt include `Working...` then `Done.`
   - Slash commands, unknown slash, blank input, exit/quit do not include `Working...` or `Done.`

3. Safety
   - Startup, slash surfaces, doctor, recovery hints, normal prompt, and multiline prompt do not leak API keys, raw prompts in status lines, hidden reasoning markers, raw JSON payloads, or raw `.env` contents.

4. Bounds
   - Startup header remains compact.
   - Unknown slash and recovery hints remain short.
   - `/doctor` and `/setup` stay plain text, not dashboard/table output.

## Scope

Primary files:

- `evals/run_evals.py`
- `tests/test_cli.py` only if necessary for focused CLI assertions
- `agent_tasks/B_DONE.md`

Do not edit:

- `mini_agent/cli.py` unless PM explicitly asks after reviewing TASK-151.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Coverage Quality Requirements

- No tautological assertions.
- Use tempdir-isolated roots and explicit settings/env/fake agent objects.
- Assert exact or meaningfully specific substrings.
- Assert secrets/API keys/raw prompts are not leaked.
- Keep evals deterministic/offline.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-151 is not integrated into your worktree yet and required checks cannot pass without runtime changes, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
