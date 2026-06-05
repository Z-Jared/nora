# TASK-122: Deterministic eval coverage for skill manifest catalog summary v1

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Codex PM assigned you TASK-122 after TASK-119 landed in `09ebf80`.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/CHAT_INDEX.md`
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`
- `agent_tasks/BACKLOG.md`

## Goal

Add deterministic offline eval coverage for the TASK-119 skill manifest catalog summary surface.

Primary target: `evals/run_evals.py`.

Do not change runtime behavior unless an eval reveals a real bug; if so, keep the runtime fix tiny and call it out clearly in `B_DONE.md`.

## Required Coverage

Add eval cases for direct or registry use of `summarize_skill_manifests` / `summarize_skill_manifests` registry tool.

Cover at least:

1. Tool registration and exact permission:
   - `ToolPermission(category="local", risk="read")`
2. Valid catalog summary:
   - `valid_count`, bounded `skills`, sorted/deduplicated domains/capabilities/workflows/deliverables/required_plugins/risk_boundaries/evals
3. Bounds:
   - default max behavior or explicit `max_skills`
   - high values clamp to the upper bound
   - zero/low values clamp safely
4. Malformed input:
   - malformed outer JSON
   - malformed individual manifest
   - non-list input
5. Secret no-leak:
   - secret-like name/version/list fields are absent or redacted
   - raw malformed secret content is not echoed
6. Read-only:
   - durable task, worker, and event counts unchanged
7. Compatibility:
   - `inspect_skill_manifest`, `route_capability_request`, and existing skill/capability evals still pass with the new evals present

## Constraints

- Evals must be deterministic and offline.
- Use tempdir-isolated `NoraDB` / registry patterns already present in `evals/run_evals.py`.
- Avoid network, LLM, external services, or shared mutable state.
- Do not edit `mini_agent/skills.py` unless you find a genuine bug.
- Do not edit A task/done files, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_skills tests.test_mini_agent
git diff --check
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
