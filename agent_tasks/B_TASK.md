# TASK-172B: TTS text fallback deterministic eval and safety coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is in progress. Voice Profile v1 is integrated. Phase 2 still uses A/B only; do not open or assume Claude C/D because current voice/presence work still shares core files. Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `evals/run_evals.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`

## Goal

Add deterministic eval and safety coverage for the Phase 2 TTS adapter boundary and text fallback preview. Coverage should lock the public contract that TASK-172A implements without adding real TTS or changing product implementation files.

Expected coverage areas:

- Text fallback is available without provider configuration.
- Voice/TTS preview exposes deterministic cost and no-audio fallback metadata.
- Secret-like preview text is rejected and not echoed.
- Preview/read endpoints do not mutate food balance, pet state, activity, or relationship memory.
- UI copy does not imply voice cloning, recording by default, always listening, hidden background activity, real payment, marketplace, or purchase pressure.

## Scope

Allowed files:

- `evals/run_evals.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `agent_tasks/B_DONE.md`

Do not edit implementation files:

- `mini_agent/tts.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `mini_agent/pets.py`

## Required Coverage

Add evals whose names include `tts` or `voice_cost`, for example:

- `tts_text_fallback_available`
- `tts_preview_cost_transparent`
- `tts_preview_rejects_secret_text`
- `tts_preview_read_only_no_food_or_state_mutation`
- `tts_webui_no_recording_or_background_copy`

Guard evals so they can explain missing TASK-172A behavior during isolated worker runs, but after PM combines with TASK-172A they must be active/pass and not permanently skipped.

## Non-Goals

- Do not implement TTS runtime behavior.
- Do not add real TTS, speech recognition, microphone access, audio playback, vendor adapters, PWA, desktop floating pet, billing, marketplace, or cloud sync.
- Do not weaken existing pet, voice profile, identity editor, commercial/no-manipulation, or Web UI smoke coverage.
- Do not add new Claude C/D worker files.

## Safety Boundaries

- Eval scans may allow negative boundary statements, but must block promotional or enabling language for:
  - voice cloning
  - recording by default
  - hidden background listening
  - always listening
  - hidden cost
  - subscription or purchase pressure
  - marketplace drift
- Tests must not assert only that files exist; they must lock public behavior, mutation boundaries, or copy contracts.
- Do not include real secrets or credentials in fixtures.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_http_server tests.test_webui_smoke
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes" evals/run_evals.py tests/test_http_server.py tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `B_DONE.md`.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-172B` and include:

- Summary of eval/test coverage
- Eval names added
- Exact command results
- Any coordination notes for Claude A / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
