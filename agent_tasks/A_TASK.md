# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-119: Skill manifest catalog summary v1.

Add a minimal read-only skill manifest catalog summary surface. This should summarize a list of declared skill manifest metadata without installing, loading, importing, or executing skill content. It is the next small step from single-manifest inspection toward a governed skill registry.

## Scope

- Work in `.ccb/workspaces/claude-a`.
- Main target: `mini_agent/skills.py`.
- Register a read-only registry tool named `summarize_skill_manifests` with `ToolPermission(category="local", risk="read")`.
- Add focused unit tests, preferably in `tests/test_skills.py`.
- Keep output deterministic, bounded, and safe.
- Do not edit `evals/run_evals.py` unless a tiny compatibility adjustment is strictly required.
- Do not edit `designs/` or `CODEX_TERMINAL_HANDOFF.md`.

## Suggested API

Pure helper:

```python
summarize_skill_manifests(
    skill_manifest_jsons: list[str] | None = None,
    max_skills: int = 20,
) -> dict
```

Registry wrapper may accept `skill_manifest_jsons` as a JSON string containing an array of manifest JSON strings or manifest objects.

Expected output shape can be adjusted to match local style, but should include:

```json
{
  "valid_count": 0,
  "invalid_count": 0,
  "skills": [
    {
      "name": "...",
      "version": "...",
      "domains": ["..."],
      "capabilities": ["..."],
      "workflows": ["..."],
      "deliverables": ["..."],
      "required_plugins": ["..."],
      "risk_boundaries": ["..."],
      "evals": ["..."]
    }
  ],
  "domains": ["..."],
  "capabilities": ["..."],
  "workflows": ["..."],
  "deliverables": ["..."],
  "required_plugins": ["..."],
  "risk_boundaries": ["..."],
  "evals": ["..."],
  "warnings": [],
  "errors": []
}
```

## Requirements

- Reuse existing skill manifest parser and safe-output helpers.
- Accept both JSON strings and dict objects in the pure helper.
- Malformed manifests should produce bounded safe errors while allowing other valid manifests to be summarized.
- Clamp `max_skills` to a small safe range, e.g. 1-50.
- Deduplicate and sort aggregate fields deterministically.
- Redact or omit secret-like values; never echo raw malformed manifest content or secret-like values.
- Keep it read-only: no durable task/worker/event mutation, no file loading, no imports of skill modules, no hook execution, no external calls.
- Preserve `inspect_skill_manifest`, `route_capability_request`, plugin manifest, and MCP behavior.

## Verification

Run before writing `agent_tasks/A_DONE.md`:

```bash
python3 -m unittest tests.test_skills tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

Add focused tests for valid catalog summary, invalid/malformed entries, bounds, deterministic sorting, secret no-leak, registry permission, registry wrapper JSON handling, read-only no-mutation, and compatibility with existing skill inspection.

## Completion

Write `agent_tasks/A_DONE.md` using the required report format, then run:

```bash
agent_tasks/notify_codex.sh A
```

Do not commit or push.

## Notes

- Claude B is independently adding eval coverage for TASK-117 skill-aware routing. Avoid editing `evals/run_evals.py` if possible.
- Do not edit `agent_tasks/B_TASK.md`, `agent_tasks/B_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If task scope conflicts with uncommitted work, stop and write the conflict in `agent_tasks/A_DONE.md`.
