# TASK-176A: Pet Room CSS-only idle presence signals

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is in progress. Voice Profile v1, TTS text fallback, speech bubble preview, consent/cost boundary, and CSS-only expression state mapping are integrated. The next bounded presence step is CSS-only idle/presence signals inside the existing Pet Room.

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

Add deterministic CSS-only idle/presence signals to the Pet Room robot avatar. The signals should make Nora-01 feel present on room load while staying read-only, web-first, and derived only from existing bounded state.

Suggested implementation shape:

- Add a small helper such as `presenceFromState(state)` returning bounded values:
  - presence key/class, for example `resting`, `alert`, `drifting`, `charging`, `waiting`
  - short label
  - optional detail text derived only from existing numeric state
- Add stable DOM markers near the robot avatar, for example:
  - `pet-presence-state`
  - `pet-presence-label`
  - `pet-presence-detail`
  - `data-presence` on the avatar root
  - CSS classes such as `presence-alert`, `presence-resting`, `presence-charging`
- Tie CSS-only animation pacing or opacity to the presence class, such as blink/core-pulse/antenna motion speed.
- Apply/update presence whenever the current pet is rendered/refreshed.
- Keep dynamic text escaped via DOM text APIs.

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

- CSS-only and deterministic; no LLM calls and no provider/network calls for presence mapping.
- Presence mapping must not mutate pet state, food, activity, relationship memory, expression state, or voice preview state.
- Presence must be derived only from bounded numeric state already available in `currentPet.state`.
- Pet Room still renders safely when state fields are missing or malformed.
- Existing expression state, speech bubble, and voice consent behavior must continue to pass.

## Non-Goals

- Do not implement real TTS, audio playback, speech recognition, microphone/camera/screen/location access, PWA/service worker, desktop floating pet, notifications, 3D/VRM, billing, marketplace, cloud sync, or Claude C/D worker setup.
- Do not add promotional voice cloning, recording by default, always/background listening, hidden costs, purchase pressure, surveillance, marketplace, or 3D/VRM copy.

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d" mini_agent/static/index.html tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-176A` and include:

- Summary of idle/presence mapping changes
- Public DOM markers/classes added
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
