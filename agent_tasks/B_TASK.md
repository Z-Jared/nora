# Claude B Task

Owner: Claude B
Status: assigned

## Task

TASK-120: Deterministic eval coverage for skill-aware capability routing v1.

Add deterministic offline eval coverage specifically for TASK-117's `skill_manifest_jsons` skill-aware capability routing path. Existing TASK-118 evals cover the earlier plugin-only router and skill manifest inspection; this task should prove the new skill routing bridge behavior.

## Scope

- Work in `.ccb/workspaces/claude-b`.
- Primary target: `evals/run_evals.py`.
- Do not change runtime modules unless you find a real blocker; if you do, document it clearly in `agent_tasks/B_DONE.md`.
- Keep evals offline, deterministic, and isolated with temporary local stores where needed.
- Do not edit `designs/` or `CODEX_TERMINAL_HANDOFF.md`.

## Required Eval Coverage

Add focused eval cases covering:

- Registry `route_capability_request` accepts `skill_manifest_jsons` and returns `candidate_skills`.
- Skill-only routing returns matched domains/capabilities and expected skill deliverables.
- Combined skill + plugin routing returns both `candidate_skills` and `candidate_plugins`.
- `required_plugins` and `risk_boundaries` aggregate as deterministic deduplicated top-level fields.
- High-risk skill boundary elevates top-level `risk_level` to `high`.
- Malformed outer skill manifest JSON and malformed individual skill manifests return bounded safe errors.
- Secret-like skill manifest `name`, `version`, list items, or unknown fields do not leak through routing.
- Skill-aware routing does not mutate durable tasks, workers, or events.
- Existing plugin-only routing eval compatibility still passes.

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

- Claude A is independently implementing TASK-119 skill manifest catalog summary. Avoid editing `mini_agent/skills.py` unless you uncover a blocker.
- Do not edit `agent_tasks/A_TASK.md`, `agent_tasks/A_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- If task scope conflicts with uncommitted work, stop and write the conflict in `agent_tasks/B_DONE.md`.
