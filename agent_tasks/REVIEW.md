# CCB Review — TASK-111/TASK-112: MCP adapter permission-aware safe surface

**Status: APPROVED**

## Findings

No blocking findings remain.

PM review found one implementation gap before approval: `registry_to_mcp_tools(...)` correctly returned only exposed MCP tools, but the TASK-111 inspection requirement also needed safe metadata for hidden/blocked tools with `exposed=false`. PM fixed this by adding `inspect_mcp_tool_surface(...)` and matching unit/eval coverage.

## Scope Reviewed

- `mini_agent/mcp_server.py`
- `tests/test_mcp_server.py`
- `evals/run_evals.py`
- `docs/knowledge/MCP_INTEGRATION.md`
- `agent_tasks/A_DONE.md`
- `agent_tasks/B_DONE.md`
- `agent_tasks/PM_INBOX.md`
- `agent_tasks/BACKLOG.md`

## Review Notes

TASK-111 hardens the MCP adapter without changing Nora's default safe MCP exposure:

- default allowlist continues to expose calculate and memory tools
- custom allowlists are still filtered by the MCP permission guard
- confirmation-required tools are blocked at the MCP boundary
- execute/interact/delete/destructive/external-send/high risk tools are blocked by default
- non-memory write tools such as `register_worker` are blocked by default
- trusted local deployments can opt in with `allow_unsafe_tools=True`
- blocked calls return bounded JSON errors without raw arguments or secret payloads
- `validate_allowlist(...)` audits custom allowlists
- `inspect_mcp_tool_surface(...)` provides safe full-surface metadata for PM/client inspection

TASK-112 adds deterministic offline eval coverage for the safe tool surface, including default/custom allowlist boundaries, unsafe custom allowlist guardrails, safe JSON errors/no-leak, bounded output, memory compatibility, and the new inspection surface.

Selective integration note: both CCB worktrees were stale relative to current `main`, so PM integrated only the TASK-111/TASK-112 relevant files and avoided reintroducing stale TASK-109/TASK-110 changes.

## Verification

```text
python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache
Ran 182 tests in 7.844s — OK

python3 evals/run_evals.py
423 passed, 0 failed

git diff --check
clean
```

## Decision

Approved for local integration. TASK-111 and TASK-112 satisfy the MCP/plugin runtime hardening slice and are ready to commit.
