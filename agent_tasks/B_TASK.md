# TASK-171B: Voice Profile v1 deterministic eval and safety coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 1 is complete and Phase 2 is ready to start. Phase 2 starts with A/B only; do not open or assume Claude C/D. Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `evals/run_evals.py`
- `tests/test_pets.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`

## Goal

Add deterministic eval and safety coverage for Voice Profile v1.

Cover the public contract planned in `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`:

- default profile is local preset metadata, not cloning
- bounded fields: `voice_id`, `speed`, `tone`, `pitch`, `expression_hints`, `speech_style_override`
- secret-like values are rejected or not leaked
- HTTP create/update paths preserve state/food/memory
- Pet Room / Identity Editor copy does not promote cloning, recording, payment, marketplace, or background listening

## Scope

Allowed files:

- `evals/run_evals.py`
- `tests/test_pets.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `agent_tasks/B_DONE.md`

Do not edit implementation files:

- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`

## Required Coverage

Add evals whose names include `voice_profile`, for example:

- `voice_profile_default_no_cloning`
- `voice_profile_fields_bounded`
- `voice_profile_rejects_secret_or_audio_sample`
- `voice_profile_http_create_update_contract`
- `voice_profile_webui_no_promotional_voice_copy`

Guard evals so they can explain missing TASK-171A behavior during isolated worker runs, but after PM combines with TASK-171A they must be active/pass and not permanently skipped.

## Non-Goals

- Do not implement Voice Profile runtime behavior.
- Do not add real TTS, speech recognition, microphone access, audio playback, vendor adapters, PWA, desktop floating pet, billing, marketplace, or cloud sync.
- Do not weaken existing pet, identity editor, commercial/no-manipulation, or Web UI smoke coverage.

## Safety Boundaries

- Eval scans may allow negative boundary statements, but must block promotional or enabling language for:
  - voice cloning
  - recording by default
  - hidden background listening
  - hidden cost
  - subscription or purchase pressure
  - marketplace drift
- Tests must not assert only that files exist; they must lock public behavior or copy contracts.
- Do not include real secrets or credentials in fixtures.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|checkout now|subscribe now|marketplace|real payment" evals/run_evals.py tests/test_pets.py tests/test_http_server.py tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `B_DONE.md`.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-171B` and include:

- Summary of eval/test coverage
- Which eval names were added
- Exact command results
- Any coordination notes for Claude A / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
