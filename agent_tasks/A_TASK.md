# TASK-163: Relationship memory MVP for pet shared moments

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora is now a customizable electronic pet agent. TASK-161/162 completed the transparent token food estimate/status loop. The next Phase 1 priority is Relationship Memory: task results, preferences, and shared moments should become part of the pet relationship, not just transient UI text.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Build a deterministic Relationship Memory MVP for the pet loop.

Required behavior:

1. Pet memory model/store:
   - Add a bounded relationship memory record type, for example `PetRelationshipMemory`.
   - Suggested fields: `memory_id`, `pet_id`, `kind`, `summary`, `source`, `importance`, `metadata`, `created_at`.
   - Supported `kind` should be a small deterministic set such as `shared_moment`, `preference`, `task_outcome`.
   - Reject secret-like text in summary, source, kind, and metadata values.
   - Bound summary/source lengths and list/read limits.
   - Use existing pet persistence patterns in `PetStore`; keep JSONL/SQLite behavior consistent with nearby pet records.

2. HTTP/API:
   - Add `POST /pet/relationship-memory` to record a memory.
   - Add `GET /pet/relationship-memory?pet_id=...&limit=...` to list recent memories.
   - Mutation endpoint must retain auth when `NORA_API_TOKEN` is set.
   - Responses must be bounded and not leak raw secret-like input.
   - Add concise docs entry to `/docs`.

3. Pet Room UI:
   - Add a small relationship memory section in Pet Room.
   - Show recent memory summaries safely.
   - Include a local-only demo/shared moment control or use existing action flow to create one.
   - Escape all rendered memory text.
   - Avoid fake intimacy, guilt, urgency, or manipulative copy.

## Non-Goals

- No vector RAG.
- No external memory provider.
- No LLM calls.
- No cross-device sync.
- No voice, 3D/VRM, marketplace, or billing work.
- No CLI/TUI redesign.

## Safety Boundaries

- Model output must not directly write memory.
- Secret-like text must be rejected before persistence.
- HTML must escape memory content.
- Mutation endpoints must honor existing HTTP auth behavior.
- Do not touch unrelated CLI/TUI/runtime code.

## Scope

Primary files:

- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_pets.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

If full evals fail because of pre-existing unrelated state, report the exact failure and still run the targeted API/UI tests.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and the public contract TASK-164 should lock.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
