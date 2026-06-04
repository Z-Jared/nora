# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-112: Deterministic eval coverage for MCP adapter safe tool surface v1

## Worktree Safety

Before editing, run `git status --short --branch`.

Your CCB worktree may still contain stale TASK-110 changes. If dirty files are unrelated to this task and are not already integrated in `main`, stop and write the conflict in `agent_tasks/B_DONE.md`. Do not stack TASK-112 on top of unresolved old work.

## Context

Nora already exposes selected `ToolRegistry` tools through the optional MCP server adapter. Existing evals cover optional dependency behavior, basic metadata export, safe allowlist, bounded output, memory compatibility, and failure isolation.

The next Agent OS direction is MCP/plugin runtime hardening. Before adding broader external connectors, Nora needs stronger deterministic eval coverage for the MCP adapter's safe tool surface and permission boundaries.

## Goal

Add focused deterministic offline eval coverage in `evals/run_evals.py` for the MCP adapter's safe tool surface.

## Requirements

Add eval cases that verify:

- Default MCP metadata export is deterministic and bounded.
- Default allowlist exposes the expected safe tools and does not expose shell, Git, browser, process, filesystem write, task mutation, destructive, external-send, high-risk, or confirmation-required tools.
- Current low-risk memory write tools in `DEFAULT_ALLOWLIST` continue to work through `call_mcp_tool`.
- A custom allowlist cannot leak handler exception details or raw secret sentinels.
- Disallowed and unknown tool errors are safe JSON and do not echo raw argument payloads.
- Long output truncation remains bounded and does not leak the hidden tail sentinel.
- Existing `registry_to_mcp_tools`, `is_tool_allowed`, and `call_mcp_tool` behavior remains compatible with `tests/test_mcp_server.py`.

Keep evals deterministic and offline: use temporary directories/local `NoraDB`, no network, no model calls, no shared state.

## Tests

Run:

```text
python3 evals/run_evals.py
python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
git diff --check
```

## Boundaries

- Edit only:
  - `evals/run_evals.py`
  - `agent_tasks/B_DONE.md`
  - `agent_tasks/PM_INBOX.md` only via `agent_tasks/notify_codex.sh B`
- Do not change runtime behavior. If an eval exposes a real MCP adapter bug, stop and describe it in `B_DONE.md`.
- Do not edit `mini_agent/mcp_server.py`; that is Claude A's scope.
- Do not edit `agent_tasks/A_TASK.md` or `agent_tasks/A_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/B_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh B
```
