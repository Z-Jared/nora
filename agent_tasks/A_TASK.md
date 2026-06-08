# TASK-165: Identity Editor MVP for pet customization

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora is now a customizable electronic pet agent. Relationship Memory has landed in `c676cc0`, so Phase 1 moves to letting each user define the pet's identity from the Pet Room.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `agent_tasks/BACKLOG.md`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_pets.py`
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

Build an Identity Editor MVP for existing pets.

Required behavior:

1. Pet store/API:
   - Add a deterministic update method for `PetIdentity` fields:
     - `name`
     - `species`
     - `personality_traits`
     - `relationship_role`
     - `speech_style`
     - `voice_profile`
     - `taste_profile`
     - `skills`
   - Preserve existing `pet_id` and `created_at`.
   - Update `updated_at`.
   - Do not reset `PetState`, compute food balance, activity events, or relationship memories.
   - Reuse existing secret validation from `create_pet` for strings/lists/dicts.
   - Reject unknown field types with bounded errors.

2. HTTP:
   - Add a mutation endpoint such as `POST /pet/update-identity`.
   - Mutation endpoint must honor existing HTTP auth behavior when `NORA_API_TOKEN` is set.
   - Return the updated pet record or identity in bounded JSON.
   - Add concise `/docs` entry.

3. Pet Room UI:
   - Add a compact Identity Editor section in the Pet Room.
   - Show current identity fields.
   - Allow editing a practical MVP subset at minimum:
     - name
     - species
     - relationship_role
     - speech_style
     - personality_traits
     - skills
   - Voice/taste can be editable as simple JSON textareas or compact key fields, as long as input is bounded and invalid JSON is handled cleanly.
   - Escape all rendered identity text.
   - Avoid fake intimacy, purchase pressure, or marketplace language.

## Non-Goals

- No 3D/VRM.
- No voice synthesis or voice cloning.
- No avatar asset generation.
- No account/cloud sync.
- No billing, marketplace, or plugin store.
- No CLI/TUI redesign.
- No LLM calls.

## Safety Boundaries

- Secret-like identity text must be rejected before persistence.
- HTML must escape identity content.
- Model output must not directly mutate identity.
- Updating identity must not clear state, food balance, activity, or relationship memories.
- Do not touch unrelated runtime/CLI code.

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

If full evals fail because of unrelated baseline state, report the exact failure and still run targeted tests.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and the public contract TASK-166 should lock.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
