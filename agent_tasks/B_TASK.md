# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-116: Skill manifest schema and inspection v1.

Implement a minimal read-only skill manifest schema / parser / inspection surface. This is the skill-pack counterpart to plugin manifests: it should let Nora inspect declared skill-pack metadata for domains, capabilities, workflows, deliverables, required plugins, risk boundaries, and eval hooks without loading or executing skill content.

## Scope

- Work in `.ccb/workspaces/claude-b`.
- Prefer a small new module such as `mini_agent/skills.py` if no equivalent module exists.
- Register a read-only registry tool named `inspect_skill_manifest` with `ToolPermission(category="local", risk="read")`.
- Keep the parser independent from plugin loading and runtime execution.
- Keep output deterministic, bounded, and safe.
- Do not edit `designs/` or `CODEX_TERMINAL_HANDOFF.md`.

## Manifest Fields

Support a v1 JSON/dict manifest with at least:

- `name` (required, non-empty string)
- `version` (required, non-empty string)
- `description` (optional, bounded)
- `domains` (optional list of strings)
- `capabilities` (optional list of strings)
- `workflows` (optional list of strings)
- `deliverables` (optional list of strings)
- `required_plugins` (optional list of strings)
- `risk_boundaries` (optional list of strings)
- `evals` (optional list of strings)

Unknown additional fields may be ignored or reported as warnings, but raw sensitive values must not leak.

## Requirements

- Provide parser/inspection helpers for dict and JSON string input, similar in spirit to `mini_agent/plugins.py`.
- Validate required fields and list field types.
- Normalize or omit malformed optional entries safely.
- Redact or omit secret-like values in names, lists, warnings, and errors.
- Bound long descriptions/list items and cap list lengths to keep output small.
- `inspect_skill_manifest` must be read-only: no durable task/worker/event mutation.
- Do not load files, import skill modules, execute hooks, call external services, or invoke plugin code.
- Preserve existing plugin manifest and MCP behavior.

## Verification

Run these before writing `agent_tasks/B_DONE.md`:

```bash
python3 -m unittest tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

Add focused unit tests for the new skill manifest parser/inspection surface. If you add tests, include the exact test command in `agent_tasks/B_DONE.md`.

## Completion

Write `agent_tasks/B_DONE.md` using the required report format, then run:

```bash
agent_tasks/notify_codex.sh B
```

Do not commit or push.

## Notes

- Claude A is working independently on TASK-115 capability router scaffold. If you both touch `mini_agent/toolkits/registry_builder.py`, keep your edit tightly scoped and document it.
- Do not edit `agent_tasks/A_TASK.md`, `agent_tasks/A_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If task scope conflicts with uncommitted work, stop and write the conflict in `agent_tasks/B_DONE.md`.
