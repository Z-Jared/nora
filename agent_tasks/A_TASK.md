# TASK-171A: Voice Profile v1 contract implementation

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

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
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_pets.py`
- `tests/test_http_server.py`

## Goal

Implement the Voice Profile v1 data contract for Nora pet identity.

The contract should allow and normalize bounded local profile fields:

- `voice_id`
- `speed`
- `tone`
- `pitch`
- `expression_hints`
- `speech_style_override`

The behavior must apply to:

- `PetStore.create_pet()`
- `PetStore.update_identity()`
- `POST /pet/create`
- `POST /pet/update-identity`
- Pet Room Identity Editor if it already exposes `voice_profile`

## Scope

Allowed files:

- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_pets.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Required Behavior

- Store Voice Profile v1 as local preset/metadata only, not as audio, recording, or a real-person clone reference.
- Preserve existing pet state, food balance, activity, and relationship memories when updating voice profile.
- Reject non-dict `voice_profile`.
- Reject secret-like values in nested fields.
- Reject or strip unsafe fields such as audio samples, speaker embeddings, real-person clone hints, raw provider credentials, or overly long values.
- Keep output bounded and deterministic.
- Keep backward compatibility for existing profiles that only contain `voice_id`, `speed`, or `tone`.

## Non-Goals

- Do not implement TTS, speech recognition, microphone access, audio playback, vendor adapters, PWA, desktop floating pet, 3D/VRM, billing, marketplace, account sync, or cloud sync.
- Do not modify `evals/run_evals.py`; Claude B owns eval coverage.
- Do not claim Phase 2 voice features are shipped.

## Safety Boundaries

- No voice cloning by default.
- No recording by default.
- No hidden background listening.
- No purchase pressure, subscription pressure, or marketplace drift.
- No API keys, provider secrets, raw audio, speaker embeddings, or real-person clone hints in stored identity or UI.

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|checkout now|subscribe now|marketplace|real payment" mini_agent/pets.py mini_agent/http_server.py mini_agent/static/index.html tests/test_pets.py tests/test_http_server.py tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-171A` and include:

- Summary of implementation changes
- Public contract changes
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
