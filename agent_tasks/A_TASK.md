# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-111: MCP adapter permission-aware tool surface hardening v1

## Worktree Safety

Before editing, run `git status --short --branch`.

Your CCB worktree may still contain stale TASK-109 changes. If dirty files are unrelated to this task and are not already integrated in `main`, stop and write the conflict in `agent_tasks/A_DONE.md`. Do not stack TASK-111 on top of unresolved old work.

## Context

Nora already has an optional MCP server adapter in `mini_agent/mcp_server.py`. It exposes a safe default allowlist and dispatches through `ToolRegistry.call()`, but the MCP surface still lacks enough permission metadata and custom-allowlist guardrails for the newer Agent OS direction.

The next direction is MCP/plugin runtime hardening: external tool surfaces must be permission-aware, inspectable, bounded, and harder to accidentally expose as high-risk tools.

## Goal

Harden the MCP adapter so callers can inspect safe registry permission metadata for exposed tools, and so custom allowlists cannot accidentally expose high-risk or confirmation-required tools without an explicit opt-in.

## Requirements

- Keep `mini_agent.mcp_server` importable without the optional `mcp` package.
- Preserve the existing default MCP behavior for safe default tools, including memory tools.
- Add pure-Python helper(s) for safe MCP tool-surface inspection. The output should include only bounded metadata:
  - tool name
  - description
  - input schema
  - permission category
  - permission risk
  - whether confirmation is required
  - whether the tool is exposed by the effective allowlist
- Add a permission guard for custom allowlists:
  - safe read tools remain callable
  - low-risk memory writes currently in `DEFAULT_ALLOWLIST` remain callable
  - shell/git/browser/process/file/task destructive or confirmation-required tools must not become callable through a custom allowlist unless an explicit unsafe opt-in parameter is provided
  - blocked calls must return a bounded JSON error without raw arguments or secrets
- Keep output truncation behavior.
- Keep handler exception failure isolation/no secret leakage.
- Update `docs/knowledge/MCP_INTEGRATION.md` to document the permission-aware surface and custom-allowlist guardrail.
- Add focused unit tests in `tests/test_mcp_server.py`.

## Tests

Run:

```text
python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
python3 evals/run_evals.py
git diff --check
```

## Boundaries

- Edit only:
  - `mini_agent/mcp_server.py`
  - `tests/test_mcp_server.py`
  - `docs/knowledge/MCP_INTEGRATION.md`
  - `agent_tasks/A_DONE.md`
  - `agent_tasks/PM_INBOX.md` only via `agent_tasks/notify_codex.sh A`
- Do not edit `evals/run_evals.py`; that is Claude B's scope.
- Do not edit `agent_tasks/B_TASK.md` or `agent_tasks/B_DONE.md`.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/`.
- Do not commit or push.

## Completion Report

Write `agent_tasks/A_DONE.md`, then run:

```text
agent_tasks/notify_codex.sh A
```
