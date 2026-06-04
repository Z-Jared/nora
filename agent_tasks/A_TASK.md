# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-115: Capability router scaffold v1.

Implement a minimal read-only capability routing scaffold. The router should inspect user goals plus declared plugin manifest metadata and return candidate capabilities, risk level, required confirmations, and expected deliverables. It must not load plugins, execute plugin code, call external services, mutate durable state, or perform tool actions.

## Scope

- Work in `.ccb/workspaces/claude-a`.
- Prefer a small new module such as `mini_agent/capability_router.py`.
- Reuse TASK-113 plugin manifest inspection/parsing helpers from `mini_agent/plugins.py`.
- Register a read-only registry tool named `route_capability_request` with `ToolPermission(category="local", risk="read")`.
- Keep behavior deterministic and bounded.
- Do not edit `designs/` or `CODEX_TERMINAL_HANDOFF.md`.

## Suggested API

Keep the public surface simple and stable:

```python
route_capability_request(
    goal: str,
    plugin_manifest_jsons: list[str] | None = None,
    max_candidates: int = 5,
) -> dict
```

The registry tool may accept `plugin_manifest_jsons` as a JSON string containing an array of manifest JSON strings or manifest objects, if that fits existing registry patterns better.

Expected output shape:

```json
{
  "goal_summary": "...",
  "risk_level": "low|medium|high",
  "requires_confirmation": false,
  "expected_deliverables": ["..."],
  "candidate_plugins": [
    {
      "name": "...",
      "version": "...",
      "matched_domains": ["..."],
      "matched_capabilities": ["..."],
      "risk_level": "low|medium|high",
      "requires_confirmation": false,
      "tool_count": 1
    }
  ],
  "warnings": [],
  "errors": []
}
```

If you need to adjust names slightly to match existing style, keep them deterministic and document the final shape in `agent_tasks/A_DONE.md`.

## Requirements

- Match plugins by simple deterministic keyword overlap across goal text, manifest domains, capabilities, tool names, and tool descriptions.
- Infer risk from matched plugin tools and goal words. High/destructive/external-send plugin tools should raise risk and require confirmation.
- Return safe bounded output only. Do not echo secret-like manifest values or raw malformed manifest content.
- Malformed manifests should produce bounded safe errors while allowing other valid manifests to be considered.
- Empty or unrelated manifests should return no candidates plus safe warnings/errors as appropriate.
- Inspection must be read-only: no durable task/worker/event mutation.
- Plugin code execution is forbidden. Do not call `load_plugins`.

## Verification

Run these before writing `agent_tasks/A_DONE.md`:

```bash
python3 -m unittest tests.test_plugins tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

Add focused unit tests if you add a new module or helper surface.

## Completion

Write `agent_tasks/A_DONE.md` using the required report format, then run:

```bash
agent_tasks/notify_codex.sh A
```

Do not commit or push.

## Notes

- Claude B is working independently on TASK-116 skill manifest schema/inspection. If you both touch `mini_agent/toolkits/registry_builder.py`, keep your edit tightly scoped and document it.
- Do not edit `agent_tasks/B_TASK.md`, `agent_tasks/B_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If task scope conflicts with uncommitted work, stop and write the conflict in `agent_tasks/A_DONE.md`.
