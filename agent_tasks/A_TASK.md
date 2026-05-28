# Claude A Task

Owner: Claude A
Status: assigned

## Goal

Integrate Nora run tracing into the default runtime and expose read-only trace inspection.

## Instructions

Implement only trace integration and read-only inspection. Do not change trace schema unless required for the inspection path.

Context:

- The first trace slice is merged in `mini_agent/traces.py`, `mini_agent/controller.py`, and `mini_agent/database.py`.
- Current gap: `build_agent()` does not pass a `TraceStore`, so normal CLI/HTTP runs do not persist traces.
- Current gap: there is no user-facing way to list or inspect traces.

Required:

- Wire `TraceStore(db=db)` into `MiniAgent` in `mini_agent/app.py`.
- Add read-only registry tools:
  - `list_run_traces(max_results=20)`
  - `get_run_trace(trace_id)`
- Add CLI commands:
  - `/traces [n]`
  - `/trace <trace_id>`
- Keep output concise and redacted. Do not expose full prompts, full model outputs, or full tool results.
- Update README command/tool docs if user-visible commands are added.
- Add focused tests for default build wiring if practical, trace tools, and CLI commands.

## Current PM Note

Trace spine exists but is not yet part of the normal product path. This task turns it from an internal library into operational runtime infrastructure.

## Completion Report

Update `agent_tasks/A_DONE.md` with:

- Summary of trace integration and inspection commands/tools.
- Diff stat.
- Exact tests run and results.
- Any known limitations.
