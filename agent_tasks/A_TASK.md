# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-113: Plugin manifest schema and inspection v1.

在现有 `mini_agent/plugins.py` 基础上增加插件 manifest v1 的解析、校验和安全只读 inspection 能力。目标是为 Nora 的 Plugin Runtime / Capability Router 打基础，但本任务只做 metadata/runtime-safe inspection，不执行外部插件动作、不接入真实 auth。

## Scope

- Add a small manifest model/parser/validator, preferably in `mini_agent/plugins.py` unless the file becomes unwieldy.
- Support manifest input as a Python `dict` and as JSON text.
- Define a stable manifest v1 shape with at least:
  - plugin identity: `name`, `version`, optional `description`
  - `auth`: method such as `none`, `oauth`, `api_key`, `local_token`, `enterprise_connector`
  - `tools`: list of tool metadata with `name`, `description`, `permission_category`, `risk`, `requires_confirmation`, `data_sensitivity`, `event_log`
  - optional routing metadata such as `domains` or `capabilities` if useful, but keep the first slice small.
- Validation must reject or safely report:
  - missing required identity fields
  - malformed/non-list `tools`
  - duplicate tool names
  - unknown auth methods
  - unknown permission categories/risks/data sensitivity labels/event-log modes
  - high-risk or external-send/destructive/financial actions without confirmation
- Add a registry-facing read-only tool, e.g. `inspect_plugin_manifest(...)`, that returns bounded safe JSON metadata and validation errors.
- Register the new inspection tool with `ToolPermission(category="local", risk="read")`.
- Preserve existing `load_plugins(...)` behavior and optional broken plugin warning behavior.

## Safety Requirements

- Do not execute plugin code from manifest inspection.
- Do not call network, browser, shell, Git, or real auth.
- Do not persist raw secrets, API keys, tokens, request payloads, or env-like values in output.
- Output should be deterministic, bounded, and safe for durable event/log inspection.
- Keep default custom implementation. Do not introduce LangChain or LangGraph.

## Suggested Tests

- Add focused unit tests, likely `tests/test_plugins.py`, covering:
  - valid developer/productivity manifest parses and returns safe metadata
  - duplicate tool names are rejected
  - high-risk/external-send/destructive/financial tool without confirmation is flagged
  - secret-like auth/token fields are not echoed
  - malformed JSON and malformed field types return bounded safe errors
  - `load_plugins(...)` existing behavior still works for simple plugin files and broken plugin warning behavior is not broken
  - `list_tool_permissions` includes the read-only inspection tool if you register it through the standard toolkit path

## Verification

Run these before writing `agent_tasks/A_DONE.md`:

```bash
python3 -m unittest tests.test_plugins tests.test_mcp_server tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If `tests.test_plugins` does not exist yet, create it.

## Completion

Write `agent_tasks/A_DONE.md` using the required report format, then run:

```bash
agent_tasks/notify_codex.sh A
```

Do not commit or push.

## Notes

- Work only in `.ccb/workspaces/claude-a`.
- Do not edit `agent_tasks/B_TASK.md`, `agent_tasks/B_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If you find task scope conflicts with existing uncommitted work, stop and write the conflict in `agent_tasks/A_DONE.md`.
