# Claude A Task

Owner: Claude A
Status: assigned

## Goal

Implement the first vertical slice of Nora run tracing.

## Instructions

Implement only the trace foundation. Do not refactor unrelated controller, logging, or HTTP code.

Required behavior:

- Add a lightweight run trace data model and store.
- Record one trace per `MiniAgent.run_events()` turn.
- Trace must include:
  - `trace_id`
  - created timestamp
  - final status
  - user input preview, redacted/truncated
  - event counts by type
  - tool calls with name/status/result preview only
  - failure text when blocked/error
- Support both SQLite-backed storage and JSONL fallback, matching existing store patterns.
- Add a read-only method/tool/API only if it is small and follows existing patterns; otherwise keep this as an internal store plus tests.
- Do not store raw API keys, tokens, full prompts, full model outputs, or full tool results.

Suggested files:

- `mini_agent/database.py`
- `mini_agent/controller.py`
- new `mini_agent/traces.py`
- `tests/test_mini_agent.py`
- new focused `tests/test_traces.py` if cleaner

## Current PM Note

Frontier direction from Codex/Claude Code/Agents SDK: traceability is now core runtime infrastructure, not a debugging extra. This task should build the smallest reliable trace spine before we add hooks, worker isolation, or evals.

## Completion Report

Update `agent_tasks/A_DONE.md` with:

- Summary of trace behavior and schema.
- Diff stat.
- Exact tests run and results.
- Any known limitations.
