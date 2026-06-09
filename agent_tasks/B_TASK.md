# TASK-177B: Room-load greeting deterministic eval and safety coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is in progress. TASK-177A will add a deterministic text-only room-load greeting to the existing Pet Room. Your job is deterministic eval/smoke/safety coverage only. Phase 2 still uses A/B only; do not open or assume Claude C/D.

Read first:

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

## Goal

Add deterministic coverage for the room-load greeting that TASK-177A implements. Coverage should lock the public contract without implementing the UI mapping yourself.

Expected coverage areas:

- Pet Room exposes stable greeting DOM markers/attributes.
- JS mapping derives greeting from existing bounded state fields and a coarse time bucket.
- Missing/malformed state and malformed date/time inputs fall back to bounded safe greeting text.
- Greeting update is read-only: no fetch, food debit, state mutation, activity write, relationship-memory write, voice-preview call, consent mutation, microphone/camera/screen/location access, provider call, service worker, desktop/native code, or notification setup.
- UI copy does not imply voice cloning, recording by default, microphone use, always listening, hidden background activity, real payment, marketplace, purchase pressure, notification opt-in, PWA install, or 3D/VRM scope drift.

## Scope

Allowed files:

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted smoke tests
- `agent_tasks/B_DONE.md`

Do not edit implementation files:

- `mini_agent/static/index.html`
- `mini_agent/tts.py`
- `mini_agent/http_server.py`
- `mini_agent/pets.py`

## Required Coverage

Add evals whose names include `room_greeting` or `pet_room_greeting`, for example:

- `pet_room_greeting_markers_present`
- `room_greeting_state_time_mapping_rules`
- `room_greeting_read_only_no_fetch`
- `room_greeting_no_voice_native_pwa_or_surveillance_copy`

Guard evals so they can explain missing TASK-177A behavior during isolated worker runs, but after PM combines with TASK-177A they must be active/pass and not permanently skipped.

## Non-Goals

- Do not implement the greeting UI, CSS, or JS helper.
- Do not add real TTS, speech recognition, microphone/camera/screen/location access, audio playback, vendor adapters, PWA/service worker, notifications, desktop floating pet, billing, marketplace, cloud sync, relationship-memory writes, activity writes, or 3D/VRM.
- Do not weaken existing pet, voice profile, TTS fallback, speech bubble, voice consent, expression state, presence state, identity editor, commercial/no-manipulation, or Web UI smoke coverage.
- Do not add new Claude C/D worker files.

## Safety Boundaries

- Eval scans may allow negative boundary statements, but must block promotional or enabling language for:
  - voice cloning
  - recording by default
  - microphone/camera/screen/location access
  - always/background listening
  - hidden cost
  - surprise food debit
  - subscription or purchase pressure
  - marketplace drift
  - 3D/VRM implementation drift
  - PWA/service-worker/notification/native drift
- Tests must not assert only that files exist; they must lock mapping behavior, read-only behavior, or copy contracts.
- Do not include real secrets or credentials in fixtures.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" evals/run_evals.py tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `B_DONE.md`.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-177B` and include:

- Summary of eval/test coverage
- Eval names added
- Exact command results
- Any coordination notes for Claude A / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
