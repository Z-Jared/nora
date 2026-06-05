# TASK-128: Deterministic eval coverage for context compiler local skill catalog bridge v1

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Codex PM assigned you TASK-128 after TASK-125/TASK-126 landed locally. TASK-128 covers the eval side of TASK-127.

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

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`. Do not stack TASK-128 on stale TASK-126 work.

## Goal

Add deterministic offline eval coverage for TASK-127: context compiler local skill catalog bridge.

Primary target: `evals/run_evals.py`.

Do not change runtime behavior unless an eval reveals a genuine bug; if so, keep the runtime fix tiny and call it out clearly in `B_DONE.md`.

## Required Coverage

Add eval cases for direct and registry use of the TASK-127 bridge.

Cover at least:

1. Direct `ContextCompiler.compile(...)` with valid `skill_manifest_paths` file path adds a Skill Context Preview section.
2. Directory path discovery contributes multiple local skill manifests in deterministic order.
3. Registry `compile_context_pack` accepts `skill_manifest_paths` as a JSON string and stays `workspace/read`.
4. Manual `skill_manifest_jsons` and local `skill_manifest_paths` combine correctly.
5. Path safety:
   - traversal
   - absolute path
   - hidden directory or file
   - denied directory
   - no caller-controlled `project_root` escape
6. Malformed input:
   - malformed paths JSON
   - non-list paths input
   - invalid manifest file
7. Secret no-leak:
   - raw unsafe path sentinels
   - secret-like manifest fields
   - raw file content
8. Read-only:
   - durable task, worker, and event counts unchanged during registry compile
9. Compatibility:
   - existing manual `skill_manifest_jsons` context compiler behavior
   - git status / changed files / knowledge excerpts / memory options still work
   - existing `discover_local_skill_manifests`, `preview_skill_context`, and `list_tool_permissions` still work

## Constraints

- Evals must be deterministic and offline.
- Use tempdir-isolated project roots and existing `NoraDB` / registry patterns in `evals/run_evals.py`.
- Avoid network, LLM, external services, or shared mutable state.
- Avoid broad runtime refactors.
- Do not edit `agent_tasks/A_TASK.md`, `agent_tasks/A_DONE.md`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent
git diff --check
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
