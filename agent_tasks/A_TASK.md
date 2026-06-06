# TASK-151: Final CLI terminal copy consistency sweep

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

This is the final implementation sweep for the Nora CLI terminal redesign line. The target is stable, restrained, Claude Code-like terminal UX:

- compact startup header with Nora robot and `Nora Code`
- prompt exactly `> `
- normal model calls show `Working...` / `Done.`
- slash commands are compact plain text and do not call the model
- `/model`, `/setup`, recovery hints, unknown slash, and `/doctor` have been compacted

This task is not another redesign. It is a final consistency pass over user-visible CLI copy in `mini_agent/cli.py`.

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

Run a final CLI copy consistency sweep and make only narrow fixes.

Check these CLI surfaces:

- startup `banner()`
- `_input_status_line()`
- `_wake_panel()`
- `_model_info()`
- `_setup_info()`
- `_workers_status()`
- `_error_recovery_hint()` / `_append_recovery_hint()`
- unknown slash return
- `_slash_menu()`
- `doctor()`
- `_help()`

Fix only clear inconsistencies:

- old panel markers: `===`, `───`, boxed/table/card style in default/slash surfaces
- old Chinese long guidance in user-facing CLI output
- old startup/welcome copy such as `Nora 已启动`
- old config labels such as `Provider:`, `Model:`, `Base URL:`, `Timeout:`, `Enabled:` where the compact lower-case style now applies
- accidental hidden-reasoning/status wording such as `thinking`, `received`, `ready`, `Agent:` in default CLI surfaces
- duplicated or overly long recovery/help lines

Keep intentionally useful strings:

- `Workspace:` and `Branch:` in `/wake` if existing tests require them and the output remains compact
- `Nora doctor`
- `API key`
- `Working...` and `Done.` for normal/multiline model calls only
- technical words inside non-user-facing comments/tests are fine

## Scope

Primary files:

- `mini_agent/cli.py`
- `tests/test_cli.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `evals/run_evals.py` unless a tiny unit-test helper absolutely requires it. Claude B owns TASK-152 eval coverage.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`
- `pyproject.toml`
- `setup.py`

## Non-Goals

- No new commands.
- No fullscreen TUI, animation, streaming, colors, rich/textual/curses dependency, or UI framework.
- No hidden reasoning display.
- No Web UI redesign.
- No model router/provider behavior changes.
- No runtime/worker/plugin/tool semantic changes.
- Do not clean non-CLI JSON/API errors unless directly surfaced by `MiniAgentCLI`.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
rg -n "===|───|提示:|未知命令|输入 / 查看命令菜单|Nora 已启动|Provider:|Model:|Base URL:|Timeout:|Enabled:|Agent:" mini_agent/cli.py tests/test_cli.py evals/run_evals.py
```

If existing evals fail only because TASK-152 has not yet updated expected copy, report exact failing eval names and still make unit tests pass.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and the `rg` scan summary.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
