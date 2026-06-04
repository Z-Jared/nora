# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-114: Deterministic eval coverage for plugin manifest inspection v1.

TASK-113 has landed on `main`. Add deterministic offline eval coverage for the plugin manifest parser / validator / inspection surface.

## Scope

- Work in `.ccb/workspaces/claude-b`.
- Extend `evals/run_evals.py` with focused deterministic evals for the TASK-113 plugin manifest surface.
- Use the existing eval style near the MCP safe surface evals as a reference.
- Keep evals offline and deterministic: no network, no browser, no model calls, no real auth, no plugin execution.
- Do not change runtime behavior unless an eval exposes a genuine TASK-113 bug; if so, make the smallest fix and document it in `agent_tasks/B_DONE.md`.

## Required Coverage

Add eval cases covering at least:

- `inspect_plugin_manifest` tool is registered with exact `ToolPermission(category="local", risk="read")`.
- Valid developer/productivity manifest returns bounded safe metadata.
- Malformed JSON / non-object / malformed tools return safe bounded errors.
- Duplicate tool names and high-risk/destructive/external-send without confirmation are rejected.
- High-risk/destructive/external-send with confirmation is accepted.
- Unknown enum values for auth, permission_category, risk, data_sensitivity, and event_log are normalized safely and do not echo raw values.
- Secret-like values in auth/tools/domains/capabilities/warnings are not leaked.
- Inspection is read-only: no durable task/worker/event mutation and no plugin code execution.
- Compatibility: existing MCP evals and `list_tool_permissions` still work.

## Verification

Run these before writing `agent_tasks/B_DONE.md`:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_plugins tests.test_mcp_server tests.test_mini_agent
git diff --check
```

## Completion

Write `agent_tasks/B_DONE.md` using the required report format, then run:

```bash
agent_tasks/notify_codex.sh B
```

Do not commit or push.

## Notes

- Do not edit `agent_tasks/A_TASK.md`, `agent_tasks/A_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If task scope conflicts with uncommitted work, stop and write the conflict in `agent_tasks/B_DONE.md`.
