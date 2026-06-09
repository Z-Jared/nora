# TASK-178A: Pet Room deterministic interaction reaction surface

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is in progress. Voice Profile v1, text-only TTS fallback, speech bubble preview, consent/cost boundary, CSS-only expression mapping, CSS-only idle/presence signals, and deterministic room-load greeting are integrated. The next bounded presence step is an immediate text reaction after existing Pet Room interactions.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`

## Goal

Add a deterministic Pet Room interaction reaction surface. After existing Pet Room interactions such as feed, care, add demo food, and shared moment submission succeed, Nora-01 should show one short text-only reaction derived from bounded action type plus bounded current pet state.

Suggested implementation shape:

- Add a helper such as `reactionFromInteraction(action, state, result)` returning bounded values:
  - reaction key, for example `fed`, `cared`, `food_added`, `shared_moment`, `neutral`
  - short reaction text
  - short meta text
- Reuse `clampState()` for state fields.
- Add stable DOM markers near the avatar/speech/greeting area:
  - `pet-room-reaction`
  - `pet-room-reaction-text`
  - `pet-room-reaction-meta`
  - `data-reaction` on the reaction root
- Apply/update the reaction only after successful existing interactions.
- Render dynamic text with DOM text APIs.

## Scope

Allowed files:

- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

Do not modify:

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/tts.py`
- `mini_agent/http_server.py`
- `mini_agent/pets.py`
- payment/billing/provider/native desktop/PWA/service-worker files
- worker configuration or Claude C/D files

## Required Behavior

- Text/DOM-only and deterministic; no LLM calls and no provider/network calls beyond the existing user-triggered interaction request.
- Reaction mapping must not create extra pet state, food, activity, relationship memory, voice preview, consent, or persistence mutations.
- Reaction must be derived only from bounded action type, existing interaction result, and bounded pet state already available in the UI.
- Pet Room still renders safely when action/state/result inputs are missing or malformed.
- Existing room greeting, expression, presence, speech bubble, and voice consent behavior must continue to pass.

## Non-Goals

- Do not add or change HTTP endpoints.
- Do not implement real TTS, audio playback, speech recognition, microphone/camera/screen/location access, PWA/service worker, desktop floating pet, notifications, 3D/VRM, billing, marketplace, cloud sync, extra relationship memory write, extra activity write, or Claude C/D worker setup.
- Do not add promotional voice cloning, recording by default, always/background listening, hidden costs, purchase pressure, surveillance, marketplace, notification, PWA, or 3D/VRM copy.

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" mini_agent/static/index.html tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-178A` and include:

- Summary of interaction reaction mapping changes
- Public DOM markers/classes/attributes added
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
