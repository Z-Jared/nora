# TASK-166: Identity Editor deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Nora is now a customizable electronic pet agent. TASK-165 should add Identity Editor MVP so each user can customize the pet identity from API and Pet Room. Your job is to lock that contract with deterministic coverage.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `agent_tasks/A_TASK.md`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_pets.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `evals/run_evals.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic offline coverage for the Identity Editor MVP.

Expected TASK-165 contract to cover:

1. Store/API:
   - Existing pet identity can update name/species/personality_traits/relationship_role/speech_style/voice_profile/taste_profile/skills.
   - `pet_id` and `created_at` are preserved.
   - `updated_at` changes.
   - Pet state, compute food balance, activity events, and relationship memories are not cleared.
   - Secret-like strings in simple fields, list fields, nested dicts, voice_profile, taste_profile, and skills are rejected and not persisted.
   - Invalid field types produce bounded errors.

2. HTTP:
   - Identity update mutation endpoint exists, for example `POST /pet/update-identity`.
   - Mutation auth remains enforced when API token is configured.
   - Response is bounded and does not echo raw secret-like input.
   - `/docs` includes the identity update endpoint.

3. Web UI:
   - Pet Room contains a compact Identity Editor section.
   - Identity form markers are present for name/species/role/style/traits/skills.
   - Rendered identity text is escaped.
   - No fake intimacy, guilt, purchase pressure, marketplace, or voice-cloning language.

4. Regression:
   - Existing pet identity, token food, relationship memory, auth, no-negative balance, and Nora-01 evals remain active/pass.
   - New identity editor evals should guarded-skip if TASK-165 is absent, but be active/pass when applied with TASK-165.

## Non-Goals

- No feature implementation except tiny testability fixes directly required by observed failures.
- No external avatar pipeline, voice cloning, 3D/VRM, marketplace, billing, account/cloud sync, or CLI/TUI redesign.

## Safety Boundaries

- Tests/evals must prove secret-like text is not saved or rendered.
- Tests/evals must prove mutation auth does not regress.
- Tests/evals must prove identity update does not clear compute food or relationship memories.
- Do not weaken or skip existing token_food, relmem, Nora-01, or pet HTTP evals.

## Scope

Primary files:

- `tests/test_pets.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `evals/run_evals.py`
- `agent_tasks/B_DONE.md`

Do not edit:

- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
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

If TASK-165 is missing, run the most relevant targeted checks and report the dependency explicitly.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-165 was present in your worktree.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
