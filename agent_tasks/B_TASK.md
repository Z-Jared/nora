# TASK-126: Deterministic eval coverage for local skill manifest catalog discovery v1

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Codex PM assigned you TASK-126 after TASK-123/TASK-124 landed in `0fbd0bb`.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/CHAT_INDEX.md`
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`
- `agent_tasks/BACKLOG.md`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`. Do not stack TASK-126 on stale TASK-124 work.

## Goal

Add deterministic offline eval coverage for TASK-125 local skill manifest catalog discovery.

Primary target: `evals/run_evals.py`.

Do not change runtime behavior unless an eval reveals a real bug; if so, keep the runtime fix tiny and call it out clearly in `B_DONE.md`.

## Required Coverage

Add eval cases for direct and registry use of the TASK-125 discovery surface.

Cover at least:

1. Tool registration and exact permission.
2. Valid manifest file discovery and summary.
3. Directory discovery with multiple manifests in deterministic sorted order.
4. Bounds:
   - max scanned files
   - max file size
   - ignored non-JSON files
5. Path safety:
   - traversal
   - absolute path
   - hidden path
   - denied directories
6. Malformed input:
   - malformed JSON file
   - invalid manifest fields
   - unsupported path argument type
7. Secret no-leak:
   - raw file content
   - secret-like manifest fields
   - unsafe path sentinels
8. Read-only:
   - durable task, worker, and event counts unchanged
9. Compatibility:
   - `inspect_skill_manifest`
   - `summarize_skill_manifests`
   - `preview_skill_context`
   - `route_capability_request`
   - `compile_context_pack`
   - `list_tool_permissions`

## Constraints

- Evals must be deterministic and offline.
- Use tempdir-isolated project roots and `NoraDB` / registry patterns already present in `evals/run_evals.py`.
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
