# TASK-121: Skill context preview surface v1

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Codex PM assigned you TASK-121 after TASK-119 landed in `09ebf80`.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/CHAT_INDEX.md`
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`
- `agent_tasks/BACKLOG.md`

## Goal

Add a read-only skill context preview surface. It should take a user goal plus a bounded list of skill manifest JSON strings/objects, select relevant skill manifests using metadata only, and return safe context hints that a future context compiler can include without dumping full skill content.

This is a metadata preview only. Do not install, load, import, execute, or read skill pack content.

## Implementation Guidance

Primary target: `mini_agent/skills.py`.

Suggested pure helper:

```python
preview_skill_context(
    goal: str,
    skill_manifest_jsons: list[Any] | None = None,
    max_skills: int = 5,
) -> dict[str, Any]
```

Suggested registry wrapper:

```python
preview_skill_context_json(goal: Any, skill_manifest_jsons: Any, max_skills: int = 5) -> dict[str, Any]
```

Register a tool in `mini_agent/toolkits/registry_builder.py`:

- name: `preview_skill_context`
- permission: `ToolPermission(category="local", risk="read")`
- params: `goal`, `skill_manifest_jsons`, `max_skills`

Expected output shape should be stable and bounded, for example:

```json
{
  "goal": "...safe bounded goal...",
  "selected_count": 1,
  "invalid_count": 0,
  "context_sections": [
    {
      "skill": "software-engineering",
      "version": "1",
      "matched_domains": ["software"],
      "matched_capabilities": ["testing"],
      "workflows": ["tdd"],
      "deliverables": ["test_results"],
      "required_plugins": ["git"],
      "risk_boundaries": ["no-production-deploy"],
      "evals": ["..."]
    }
  ],
  "required_plugins": ["git"],
  "risk_boundaries": ["no-production-deploy"],
  "warnings": [],
  "errors": []
}
```

Exact field names can vary if you keep them clear and tests assert them, but include enough metadata for context compiler preview.

## Requirements

- Reuse existing skill manifest parser/safe helpers where possible.
- Match skills against `goal` using manifest metadata (`name`, `description`, `domains`, `capabilities`, `workflows`, `deliverables`) with deterministic ordering.
- Bound `max_skills` to a small safe range, e.g. 1-20.
- Output must not include raw malformed input or secret-like values.
- Include an explicit untrusted/read-only framing field or section text so downstream context cannot be treated as instructions.
- Do not mutate durable task, worker, or event state.
- Do not touch `evals/run_evals.py`; Claude B owns TASK-122.
- Do not edit `CODEX_TERMINAL_HANDOFF.md` or `designs/`.

## Tests

Add focused unit tests, likely in `tests/test_skills.py`.

Cover:
- valid relevant skill is selected with matched metadata
- irrelevant skill is skipped
- multiple selected skills are deterministic and bounded
- malformed skill input returns bounded safe errors
- secret-like values do not leak
- registry tool exists with exact `ToolPermission(category="local", risk="read")`
- registry wrapper honors `max_skills`
- read-only no durable task/worker/event mutation
- compatibility with `inspect_skill_manifest`, `summarize_skill_manifests`, and `route_capability_request`

## Required Verification

Run:

```bash
python3 -m unittest tests.test_skills tests.test_context_memory tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
