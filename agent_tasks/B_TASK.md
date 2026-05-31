# Claude B Task

Owner: Claude B
Status: completed

## Goal

TASK-041: Deterministic eval coverage for Nora MCP server adapter.

Add offline eval coverage for TASK-040 so Nora's MCP adapter stays optional, safe, and compatible with existing tools.

## Scope

Edit `evals/run_evals.py` only unless you discover a real TASK-040 runtime bug. If TASK-040 is not present yet, wait or write `agent_tasks/B_DONE.md` as blocked by missing runtime.

Do not require the external `mcp` package to be installed for evals. Do not call external APIs.

Add eval cases covering:

1. Optional dependency behavior:
   - MCP adapter can be imported without `mcp` installed if only using pure adapter helpers.
   - Stdio server entrypoint reports clear install guidance when `mcp` is missing.

2. Tool export basics:
   - Allowed tools appear in exported MCP metadata.
   - Tool names/descriptions/input schemas are stable and JSON-serializable.

3. Safety:
   - High-risk tools are not exposed by default.
   - Disallowed tool calls return JSON errors, not exceptions.
   - Output is bounded and does not leak env vars, raw shell output, prompts, diffs, or unrelated event payloads.

4. Compatibility:
   - Existing `ToolRegistry` and OpenAI-style tool metadata still work.
   - Existing memory and structured memory tools work through the adapter.

5. Failure isolation:
   - Unknown tool, malformed args, missing required args, and tool handler errors are isolated into deterministic JSON errors.

Keep evals deterministic and offline.

## Verification

Run at minimum:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
git diff --check
```

If you touch anything outside `evals/run_evals.py`, also run focused tests for those files.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, exact checks run, and known limitations.

Do not commit or push.
