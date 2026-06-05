# TASK-131: CLI setup/config and response-status UX v1

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora just gained `/wake`, `/model`, `/workers`, startup worker status, and TASK-130 eval coverage. The next goal is to make the terminal feel less abrupt and easier to configure without turning this into a full UI rewrite.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/CHAT_INDEX.md`
- `agent_tasks/BACKLOG.md`
- `mini_agent/cli.py`
- `mini_agent/settings.py`
- `tests/test_cli.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Improve CLI setup/config and response-status UX v1:

1. `/setup` and `/config`
   - Add a read-only setup/config guidance command.
   - Show current provider/model/base URL/key presence without leaking key values.
   - Show concrete `.env` keys for openai-compatible, anthropic, and gemini.
   - Show safe example snippets using placeholders only, never real keys.
   - Include next-step guidance for fixing 401/missing-key/provider-model mismatch.
   - `/config` may alias `/setup` if that fits the current CLI style.

2. Response status output
   - When a normal prompt is handled, show deterministic status lines via `output_func` before and/or after `agent.run(...)`.
   - The status should make the CLI feel alive, e.g. model call started/completed, without exposing hidden reasoning or chain-of-thought.
   - Keep output deterministic and testable.
   - Do not add async, streaming transport, terminal framework, or heavy dependency.
   - Do not add status noise for slash commands, blank input, or exit.

3. Markdown/plain-text polish
   - Reduce rough raw-Markdown feel in newly touched CLI outputs.
   - Avoid raw JSON for setup/config/status surfaces.
   - Keep existing command compatibility.

## Scope

Primary files:
- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Possible supporting files only if truly needed:
- `mini_agent/settings.py`

Do not edit:
- `evals/run_evals.py` — Claude B owns TASK-132 eval coverage.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## UX Constraints

- Never print raw API keys, tokens, `.env` values, full secrets, or private file contents.
- Do not show hidden reasoning or chain-of-thought. Status lines may say what phase is happening, not why internally.
- Keep output readable in a terminal and deterministic for tests.
- Do not broaden backend runtime behavior.
- Do not change model provider semantics.

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
