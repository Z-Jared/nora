# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-118: Deterministic eval coverage for skill and capability manifest surfaces v1.

Add deterministic offline eval coverage for the just-landed TASK-115/TASK-116 surfaces: `inspect_skill_manifest` and `route_capability_request`. This task should prove read-only behavior, safe bounded outputs, secret no-leak, exact permission metadata, and compatibility without changing runtime behavior.

## Scope

- Work in `.ccb/workspaces/claude-b`.
- Primary target: `evals/run_evals.py`.
- Do not change runtime modules unless you find a real blocker; if you do, document it clearly in `agent_tasks/B_DONE.md`.
- Keep evals offline, deterministic, and isolated with temporary local stores where needed.
- Do not edit `designs/` or `CODEX_TERMINAL_HANDOFF.md`.

## Required Eval Coverage

Add focused eval cases covering:

- `inspect_skill_manifest` registry tool permission is exactly `ToolPermission(category="local", risk="read")`.
- Valid skill manifest produces bounded safe metadata.
- Malformed skill manifest JSON / non-object / invalid list fields produce bounded safe errors or warnings.
- Secret-like skill manifest values do not leak through direct or registry inspection.
- Skill manifest inspection does not mutate durable tasks, workers, or events.
- `route_capability_request` registry tool permission is exactly `ToolPermission(category="local", risk="read")`.
- Valid plugin manifest routing returns deterministic candidate metadata, risk level, confirmation flag, and expected deliverables.
- Malformed outer plugin manifest JSON and malformed individual manifests produce bounded safe errors.
- Secret-like plugin manifest name/version do not leak through routing.
- Capability routing does not mutate durable tasks, workers, or events.
- Existing plugin manifest / MCP / durable task eval compatibility still passes.

## Verification

Run before writing `agent_tasks/B_DONE.md`:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_plugins tests.test_skills tests.test_mini_agent
git diff --check
```

## Completion

Write `agent_tasks/B_DONE.md` using the required report format, then run:

```bash
agent_tasks/notify_codex.sh B
```

Do not commit or push.

## Notes

- Claude A is working independently on TASK-117 skill-aware capability routing bridge. Avoid editing `mini_agent/capability_router.py` unless you uncover a blocker.
- Do not edit `agent_tasks/A_TASK.md`, `agent_tasks/A_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If task scope conflicts with uncommitted work, stop and write the conflict in `agent_tasks/B_DONE.md`.
