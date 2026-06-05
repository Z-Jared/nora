# TASK-129 Completion Report

Status: ready for Codex review

## Summary

Implemented CLI wake/setup/status UX v1: `/wake`, `/model`, `/workers` commands, improved startup banner, and error recovery hints.

## Changes

### `mini_agent/cli.py`
- **`/wake`**: Reads project context from `docs/knowledge/PROJECT_WAKEUP.md`, `DECISIONS.md`, `CHAT_INDEX.md`, `AGENTS.md`, git status, and `agent_tasks/BACKLOG.md`. Outputs a concise project wake panel. Shows recovery guidance for missing files or non-project directories.
- **Startup banner**: Now shows workspace, branch, provider/model, API key presence (without leaking), task/backlog summary, worker state summary, and common commands hint.
- **`/model`**: Shows current provider/model/base URL/key presence. Diagnoses missing provider/model/key with concrete next steps. Includes error recovery hints for common failures.
- **`/workers`**: Shows Claude A/B / CCB worker status from `.ccb/` project files. Includes current tasks and whether A_DONE/B_DONE appear ready for PM review. Handles missing `.ccb` or task files gracefully.
- **Error recovery hints**: Added `_error_recovery_hint()` for common provider/config failures (401/unauthorized, missing key, port in use, connection timeout, unsupported provider, model not found, rate limit, quota/billing). Hints are appended to agent responses automatically.
- **Bug fix (PM review)**: `_worker_state_summary()` used `agent.split('-')[0].upper()` which gave `CLAUDE_DONE.md` instead of `A_DONE.md`. Fixed to `agent.split('-')[-1].upper()`.
- **Cleanup (PM review)**: Removed unused top-level `import json` and `import os` (both only used in local imports or not at all).

### `tests/test_cli.py`
- **`CLIWakeCommandTests`**: 5 tests for `/wake` (basic, knowledge files, missing files, no-git hint, with git).
- **`CLIModelCommandTests`**: 6 tests for `/model` (no settings, provider info, key missing, key configured, no leak, recovery hints).
- **`CLIWorkersCommandTests`**: 4 tests for `/workers` (no .ccb, shows status, shows done status, banner detects done file).
- **`CLIErrorRecoveryTests`**: 8 tests for error recovery hints (401, timeout, model not found, rate limit, missing key, port in use, no hint for normal, agent response integration).

## Verification

```
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent → 207 tests OK
python3 evals/run_evals.py → 497 passed, 0 failed
git diff --check → clean
```

## Notes

- No push performed.
- No edits to `evals/run_evals.py`, `agent_tasks/B_TASK.md`, `agent_tasks/B_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
