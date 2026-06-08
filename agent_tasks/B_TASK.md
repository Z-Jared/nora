# TASK-174B: Voice consent boundary deterministic eval and safety coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is in progress. TASK-174A will add an explicit consent and cost confirmation boundary to the text-only voice preview flow. Phase 2 still uses A/B only; do not open or assume Claude C/D. Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `evals/run_evals.py`
- `tests/test_webui_smoke.py`
- `tests/test_http_server.py`

## Goal

Add deterministic eval/safety coverage for the voice preview consent and cost confirmation boundary that TASK-174A implements. Coverage should lock the public contract without implementing UI or modifying product files.

Expected coverage areas:

- Pet Room contains stable consent/cost boundary markers.
- The preview UI does not call `/pet/voice-preview` when the confirmation checkbox is unchecked.
- `/pet/voice-preview` exposes stable consent/cost/provider/no-audio/no-recording/read-only metadata.
- The boundary copy makes text-only fallback, estimated cost, no provider/network call, no recording, and no food debit clear.
- Dynamic preview text and metadata remain escaped and do not leak secret-like content.
- UI copy does not imply voice cloning, recording by default, microphone use, always listening, hidden background activity, real payment, marketplace, or purchase pressure.

## Scope

Allowed files:

- `evals/run_evals.py`
- `tests/test_webui_smoke.py`
- `tests/test_http_server.py` only if adding a narrowly targeted public-contract test
- `agent_tasks/B_DONE.md`

Do not edit implementation files:

- `mini_agent/static/index.html`
- `mini_agent/http_server.py`
- `mini_agent/tts.py`
- `mini_agent/pets.py`

## Required Coverage

Add evals whose names include `voice_consent` or `voice_cost_confirmation`, for example:

- `voice_consent_markers_present`
- `voice_consent_unchecked_no_fetch`
- `voice_cost_confirmation_metadata`
- `voice_consent_no_recording_or_marketplace_copy`

Guard evals so they can explain missing TASK-174A behavior during isolated worker runs, but after PM combines with TASK-174A they must be active/pass and not permanently skipped.

## Non-Goals

- Do not implement the consent UI or HTTP response fields.
- Do not add real TTS, speech recognition, microphone access, audio playback, vendor adapters, PWA, desktop floating pet, billing, marketplace, or cloud sync.
- Do not weaken existing pet, voice profile, TTS fallback, speech bubble, identity editor, commercial/no-manipulation, or Web UI smoke coverage.
- Do not add new Claude C/D worker files.

## Safety Boundaries

- Eval scans may allow negative boundary statements, but must block promotional or enabling language for:
  - voice cloning
  - recording by default
  - microphone or background listening claims
  - always listening
  - hidden cost
  - surprise food debit
  - subscription or purchase pressure
  - marketplace drift
- Tests must not assert only that files exist; they must lock public behavior, mutation boundaries, or copy contracts.
- Do not include real secrets or credentials in fixtures.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes|microphone|mic access" evals/run_evals.py tests/test_webui_smoke.py tests/test_http_server.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `B_DONE.md`.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-174B` and include:

- Summary of eval/test coverage
- Eval names added
- Exact command results
- Any coordination notes for Claude A / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
