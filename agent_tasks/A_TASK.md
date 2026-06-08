# TASK-174A: Voice preview consent and cost confirmation boundary

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is in progress. Voice Profile v1, TTS text fallback, and Pet Room speech bubble preview are integrated. The next boundary is explicit consent and cost confirmation before any future real TTS/provider/audio path. Phase 2 still uses A/B only; do not open or assume Claude C/D. Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `mini_agent/tts.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`

## Goal

Add an explicit consent and cost confirmation boundary to the current text-only voice preview flow. The user should see and confirm the boundary before the Pet Room calls `/pet/voice-preview`; the endpoint response should also expose stable metadata proving the preview is text-only, cost-estimated, provider-disabled, no-recording, and read-only.

Suggested implementation shape:

- Extend the text fallback voice-preview response with stable consent/cost/provider metadata, such as:
  - `requires_user_confirmation: true`
  - `confirmation_kind: "text_fallback_voice_preview"` or similar bounded enum
  - `audio_requires_confirmation: true`
  - `provider_status: "not_configured_text_fallback"`
  - `food_debit: false`
  - keep existing `cost_tokens`, `has_audio: false`, `no_network_call: true`, and `no_recording: true`
- Add Pet Room DOM markers near the speech bubble for the confirmation boundary, for example:
  - `voice-consent-panel`
  - `voice-consent-checkbox`
  - `voice-consent-cost`
  - `voice-consent-provider`
  - `voice-consent-boundary`
- If the checkbox is not checked, show a bounded UI error and do not call `/pet/voice-preview`.
- When checked, call `/pet/voice-preview` and render the text fallback plus cost/no-audio/no-provider/no-recording/read-only metadata.
- Use DOM text APIs or existing escaping helpers for dynamic text.

## Scope

Allowed files:

- `mini_agent/tts.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

Do not modify:

- `evals/run_evals.py` (Claude B owns eval coverage)
- payment/billing/provider/native desktop/PWA files
- worker configuration or Claude C/D files

## Required Behavior

- `/pet/voice-preview` remains text-only and read-only.
- Pet Room must not fetch `/pet/voice-preview` until the user explicitly confirms the consent/cost boundary.
- UI must clearly show estimated cost, no audio, no provider/network call, no recording, and no food debit/read-only behavior.
- Errors for unchecked confirmation, invalid input, secret-like input, or over-limit input must be bounded and must not echo raw secrets or over-limit text.
- Dynamic text must be escaped through DOM text APIs or existing escaping helpers.
- No activity event, relationship memory, food debit, or pet state mutation is introduced.

## Non-Goals

- Do not implement real TTS, audio playback, speech recognition, microphone access, vendor adapters, PWA, desktop floating pet, 3D/VRM, billing, marketplace, account sync, cloud sync, or Claude C/D worker setup.
- Do not add promotional voice cloning, recording by default, always/background listening, hidden costs, purchase pressure, or marketplace copy.

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes|microphone|mic access" mini_agent/tts.py mini_agent/http_server.py mini_agent/static/index.html tests/test_webui_smoke.py tests/test_http_server.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-174A` and include:

- Summary of implementation changes
- Public HTTP response fields and DOM markers added
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
