# Claude A Task

Owner: Claude A
Status: completed

## Goal

Completed: fix `/session/list` response compatibility without removing the structured session data.

## Instructions

This task has been completed and reviewed by Codex PM. Do not continue work from this task in a new worker window.

Completed scope:

- Preserve the old HTTP contract where `body["sessions"]` is the legacy formatted string.
- Keep the new structured data under a new field such as `sessions_structured`.
- Keep `sessions_text` only if useful as an alias, but do not rely on it as the compatibility field.
- Update the Web UI to prefer the structured field and fall back to the legacy `sessions` string.
- Update or add focused tests for:
  - `/session/list` returns legacy string in `sessions`.
  - structured entries remain available.
  - empty/no-store behavior remains stable.

Suggested files:

- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_http_server_extra.py`
- `tests/test_webui_smoke.py` only if needed

## Current PM Note

Codex review found a medium compatibility issue: the last change moved the legacy string from `sessions` to `sessions_text`, which can break existing HTTP clients. This has been fixed and is waiting for the next PM assignment.

## Completion Report

Update `agent_tasks/A_DONE.md` with:

- Summary of compatibility behavior.
- Diff stat.
- Exact tests run and results.
- Any known limitations.
