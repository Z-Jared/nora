# TASK-175A: Pet Room CSS-only expression state mapping

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is in progress. Voice Profile v1, TTS text fallback, Pet Room speech bubble preview, and explicit voice preview consent/cost confirmation are integrated. The next bounded presence step is CSS-only expression state mapping from existing pet state.

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

Map existing Pet Room state (`mood`, `energy`, `hunger`) into deterministic CSS expression classes and visible state markers on the robot avatar. This should make the pet feel more present while staying fully web-first, CSS-only, and read-only.

Suggested implementation shape:

- Add a small deterministic JS helper such as `expressionFromState(state)` that returns bounded values:
  - expression key/class, for example `happy`, `sleepy`, `hungry`, `low-energy`, `calm`, `focused`
  - short display label
  - optional detail text derived only from existing numeric state
- Add stable DOM markers near or inside the robot avatar, for example:
  - `pet-expression-state`
  - `pet-expression-label`
  - `pet-expression-detail`
  - `data-expression` on the avatar root
  - CSS classes such as `expression-happy`, `expression-sleepy`, `expression-hungry`
- Apply/update the expression whenever the current pet is rendered/refreshed.
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
- payment/billing/provider/native desktop/PWA files
- worker configuration or Claude C/D files

## Required Behavior

- CSS-only and deterministic; no LLM calls and no provider/network calls for expression mapping.
- Expression mapping must not mutate pet state, food, activity, relationship memory, or voice preview state.
- Expression must be derived only from bounded numeric state already available in `currentPet.state`.
- Pet Room still renders safely when state fields are missing or malformed.
- Existing speech bubble and voice consent behavior must continue to pass.

## Non-Goals

- Do not implement real TTS, audio playback, speech recognition, microphone/camera/screen/location access, PWA, desktop floating pet, 3D/VRM, billing, marketplace, cloud sync, or Claude C/D worker setup.
- Do not add promotional voice cloning, recording by default, always/background listening, hidden costs, purchase pressure, or marketplace copy.

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access" mini_agent/static/index.html tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-175A` and include:

- Summary of expression mapping changes
- Public DOM markers/classes added
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
