# TASK-125: Local skill manifest catalog discovery v1

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Codex PM assigned you TASK-125 after TASK-123/TASK-124 landed in `0fbd0bb`.

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

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`. Do not stack TASK-125 on stale TASK-123 work.

## Goal

Add a read-only local skill manifest catalog discovery surface. Nora should be able to inspect skill manifests from project-local paths without loading, importing, installing, enabling, disabling, or executing skill code.

This is the next Skill Pack Runtime slice after manifest parsing, routing, catalog summary, preview, and context compiler bridge.

## Requirements

- Add pure-Python helper(s) in `mini_agent/skills.py` to discover and summarize local skill manifest files.
- Accept one or more project-relative paths, such as a file path or directory path.
- Directory scans should be deterministic and bounded:
  - stable sorted order
  - cap scanned manifest files
  - cap manifest file size
  - skip hidden directories, denied directories, and non-JSON files
  - reject path traversal and absolute paths
- Reuse existing skill manifest parser/summary safety logic. Do not duplicate parser behavior.
- Return only bounded safe metadata:
  - discovered paths
  - valid/invalid counts
  - safe skill metadata
  - aggregate domains/capabilities/workflows/deliverables/required_plugins/risk_boundaries/evals
  - warnings/errors
- Do not load Python modules, execute skill files, install packages, call network, or mutate durable task/worker/event/memory/trace state.
- Register a read-only registry tool, likely `discover_local_skill_manifests`, with a conservative permission such as `ToolPermission(category="workspace", risk="read")`.
- Keep existing `inspect_skill_manifest`, `summarize_skill_manifests`, `preview_skill_context`, `route_capability_request`, and context compiler behavior compatible.

## Suggested Files

- `mini_agent/skills.py`
- `mini_agent/toolkits/registry_builder.py`
- `tests/test_skills.py`
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` only if a short note is useful; avoid broad docs churn.
- `agent_tasks/A_DONE.md`

Do not edit:
- `evals/run_evals.py` — Claude B owns TASK-126.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Tests

Add focused tests in `tests/test_skills.py`.

Cover at least:
- missing path / empty path returns bounded safe errors
- valid manifest file is discovered and summarized
- directory scan discovers multiple manifests in stable order
- max file count and max file size are bounded
- traversal, absolute path, hidden path, denied directory, non-JSON file are rejected/skipped safely
- malformed JSON and invalid manifests return bounded safe errors without raw file content leak
- secret-like manifest values do not leak
- registry tool is registered with exact permission
- registry tool accepts path arguments and returns JSON string
- read-only: durable task/worker/event counts unchanged
- compatibility with existing skill manifest surfaces

## Required Verification

Run:

```bash
python3 -m unittest tests.test_skills tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
