# TASK-127: Context compiler local skill catalog bridge v1

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Codex PM assigned you TASK-127 after TASK-125/TASK-126 landed locally.

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

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`. Do not stack TASK-127 on stale TASK-125 work.

## Goal

Bridge TASK-125 local skill manifest discovery into the context compiler. Nora should be able to compile a task context pack from project-local skill manifest paths without callers first reading manifest files manually.

This advances Skill Pack Runtime by letting local skill catalogs contribute scoped, untrusted context hints through the existing context compiler path.

## Requirements

- Extend `ContextCompiler.compile(...)` with optional local skill manifest path input, likely `skill_manifest_paths`.
- Accept project-relative file or directory paths as either:
  - a list of strings for direct Python calls
  - a JSON string path list for registry calls
- Use TASK-125 `discover_local_skill_manifests_json(...)` or equivalent existing helper.
- Bind discovery to `self.root`; do not expose or trust caller-supplied `project_root`.
- Feed discovered safe manifest metadata into the existing skill context preview section.
- Preserve existing `skill_manifest_jsons` behavior. If both manual manifests and local paths are supplied, combine them deterministically.
- Include bounded safe discovery warnings/errors in the Skill Context Preview section when local discovery has warnings/errors.
- Keep all output framed as untrusted/read-only skill metadata hints.
- Do not load, import, install, enable, disable, or execute skill code.
- Do not call network or mutate durable task/worker/event/memory/trace state.
- Update registry `compile_context_pack` schema to expose the local path input, but not `project_root`.
- Keep existing context compiler behavior unchanged when no skill manifests or paths are supplied.

## Suggested Files

- `mini_agent/context_compiler.py`
- `mini_agent/toolkits/register_developer.py`
- `mini_agent/toolkits/registry_builder.py`
- `tests/test_context_compiler.py`
- `agent_tasks/A_DONE.md`

Do not edit:
- `evals/run_evals.py` — Claude B owns TASK-128.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Tests

Add focused tests in `tests/test_context_compiler.py`.

Cover at least:
- no `skill_manifest_paths` keeps existing behavior
- valid local manifest file path adds Skill Context Preview
- valid local directory path discovers multiple manifests in deterministic order
- registry `compile_context_pack` accepts `skill_manifest_paths` JSON string
- manual `skill_manifest_jsons` and local `skill_manifest_paths` combine without duplicate unsafe behavior
- malformed path input returns bounded safe error section
- traversal/absolute/hidden/denied path inputs do not leak raw unsafe content
- secret-like manifest values do not leak
- context budget still applies to discovered skill context
- compatibility with existing git/status/file/memory parameters

## Required Verification

Run:

```bash
python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
