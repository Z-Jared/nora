# TASK-124: Deterministic eval coverage for skill context preview v1

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Codex PM assigned you TASK-124 after TASK-121/TASK-122 landed in `cde4b3f`.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/CHAT_INDEX.md`
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`
- `agent_tasks/BACKLOG.md`

## Goal

Add deterministic offline eval coverage for the TASK-121 skill context preview surface.

Primary target: `evals/run_evals.py`.

Do not change runtime behavior unless an eval reveals a real bug; if so, keep the runtime fix tiny and call it out clearly in `B_DONE.md`.

## Required Coverage

Add eval cases for direct or registry use of `preview_skill_context` / registry `preview_skill_context`.

Cover at least:

1. Tool registration and exact permission:
   - `ToolPermission(category="local", risk="read")`
2. Valid skill context preview:
   - relevant skill is selected from goal/manifest metadata
   - output includes bounded context sections, required plugins, risk boundaries, eval hints, and untrusted/read-only framing
3. Determinism and bounds:
   - multiple matching skills have stable ordering
   - `max_skills` is honored
   - high, zero, negative, and bad `max_skills` values are bounded safely
4. Malformed input:
   - malformed outer JSON
   - non-list JSON
   - unsupported input type
   - invalid individual manifest entries
5. Large input:
   - input scan cap/truncation warning keeps errors and warnings bounded
6. Secret no-leak:
   - secret-like goal, name, version, malformed input, domains, capabilities, workflows, deliverables, required_plugins, risk_boundaries, and evals do not leak raw sentinel values
7. Read-only:
   - durable task, worker, and event counts unchanged
8. Compatibility:
   - `inspect_skill_manifest`, `summarize_skill_manifests`, `route_capability_request`, and `list_tool_permissions` still work with the new evals present

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
