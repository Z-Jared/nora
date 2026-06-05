# Claude A Task

Owner: Claude A
Status: assigned

## Task

TASK-117: Skill-aware capability routing bridge v1.

Extend the current read-only capability router so Nora can route against both skill manifest metadata and plugin manifest metadata. This is a bridge between TASK-115 and TASK-116: given a user goal, declared skill manifests, and declared plugin manifests, return candidate skill packs, candidate plugins, required plugins, risk boundaries, risk level, confirmation needs, and expected deliverables.

## Scope

- Work in `.ccb/workspaces/claude-a`.
- Main target: `mini_agent/capability_router.py`.
- You may add focused unit tests to `tests/test_plugins.py` or a small dedicated test file if cleaner.
- Keep `mini_agent/skills.py` parser behavior stable; reuse its existing helpers instead of duplicating schema parsing.
- If you touch `mini_agent/toolkits/registry_builder.py`, keep the edit tightly scoped to the existing `route_capability_request` registration.
- Do not edit `designs/` or `CODEX_TERMINAL_HANDOFF.md`.

## Requirements

- Add support for optional `skill_manifest_jsons` input. It may be accepted as a Python list in the pure function and as a JSON string in the registry wrapper, matching the plugin manifest pattern.
- Output must include a deterministic bounded `candidate_skills` list with at least:
  - `name`
  - `version`
  - `matched_domains`
  - `matched_capabilities`
  - `required_plugins`
  - `risk_boundaries`
  - `expected_deliverables`
- Preserve existing `candidate_plugins` behavior and backwards compatibility for callers that only pass plugin manifests.
- Aggregate `required_plugins`, skill `risk_boundaries`, and plugin risks into the top-level route result without exposing raw sensitive values.
- Do not load skill files, import skill modules, execute hooks, load plugins, call external services, mutate durable task/worker/event state, or perform tool actions.
- Malformed skill manifests should produce bounded safe errors while allowing other valid manifests/plugins to be considered.
- Keep sorting deterministic.

## Verification

Run before writing `agent_tasks/A_DONE.md`:

```bash
python3 -m unittest tests.test_plugins tests.test_skills tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

Add focused tests for skill-aware routing, malformed skill JSON, no secret leak, backwards compatibility, registry permission, and no durable mutation.

## Completion

Write `agent_tasks/A_DONE.md` using the required report format, then run:

```bash
agent_tasks/notify_codex.sh A
```

Do not commit or push.

## Notes

- Claude B is working independently on TASK-118 eval coverage for the already-landed TASK-115/TASK-116 surfaces. Avoid editing `evals/run_evals.py` unless required.
- Do not edit `agent_tasks/B_TASK.md`, `agent_tasks/B_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If task scope conflicts with uncommitted work, stop and write the conflict in `agent_tasks/A_DONE.md`.
