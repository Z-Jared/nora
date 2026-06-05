# TASK-130: CLI UX smoke/eval coverage

Status: ready for Codex review

## Summary

Added 11 deterministic offline eval cases for TASK-129 CLI wake/setup/status UX in `evals/run_evals.py`. Revised to cover the full TASK-129 surface after PM integration.

## Diff

```text
agent_tasks/B_DONE.md   |  39 ++++----
agent_tasks/PM_INBOX.md |   5 +
evals/run_evals.py      | 246 ++++++++++++++++++++++++++++++++++++++++++++++++
3 files changed, 268 insertions(+), 22 deletions(-)
```

## Changes

`evals/run_evals.py` adds 11 eval functions and 11 EvalCase registrations:

1. **`eval_cli_startup_banner_no_model`** — startup banner shows `API key: missing`, common commands (`/wake`, `/model`, `/workers`), workspace path, and safety hint when no API key configured.
2. **`eval_cli_startup_banner_with_model`** — startup banner shows configured provider/model and `API key: configured`; asserts fake secret key is not leaked.
3. **`eval_cli_startup_banner_worker_summary`** — startup banner detects `.ccb/workspaces/claude-a/agent_tasks/A_DONE.md` with "ready for review" as done.
4. **`eval_cli_wake_project_panel`** — `/wake` panel includes workspace, branch, knowledge file status (`✓ PROJECT_WAKEUP.md`, `✓ DECISIONS.md`, `✓ AGENTS.md`), and active task summary.
5. **`eval_cli_wake_non_project_guidance`** — `/wake` outside a git project shows "(not in git repo)" and recovery hints.
6. **`eval_cli_model_provider_diagnostics`** — `/model` shows provider/model/base URL/key status with no API key leak.
7. **`eval_cli_model_no_settings`** — `/model` with no settings shows setup guidance with `LLM_API_KEY` hint.
8. **`eval_cli_workers_ccb_status`** — `/workers` shows A/B task and DONE status, detects "ready for PM review", shows PM inbox path.
9. **`eval_cli_workers_no_ccb`** — `/workers` without `.ccb` directory shows graceful "未找到 .ccb/" message.
10. **`eval_cli_error_recovery_hint`** — agent responses with 401/unauthorized get recovery hint appended.
11. **`eval_cli_markdown_no_raw_json`** — all CLI surfaces (`/wake`, `/model`, `/workers`, `/help`, `/doctor`) produce human-readable Markdown/plain-text, no raw JSON.

## Verification

```text
python3 evals/run_evals.py -> 508 passed, 0 failed
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent -> 207 tests OK
git diff --check -> clean
```

## Notes

- Worktree brought to `aa3c084` (TASK-129 integration) before writing evals.
- No runtime behavior changes.
- Only `evals/run_evals.py` modified.
