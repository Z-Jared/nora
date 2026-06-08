# TASK-172A: TTS adapter protocol with text fallback

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

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
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`

## Goal

Implement the Phase 2 TTS adapter boundary as a deterministic text-fallback surface. Nora must expose a safe preview path for future speech without adding real TTS, audio playback, microphone access, provider calls, or hidden costs.

Suggested implementation shape:

- Add `mini_agent/tts.py` with bounded `TTSResult`, `TextFallbackTTSAdapter`, and deterministic cost/preview helpers.
- Add a local HTTP preview endpoint such as `POST /pet/voice-preview` that returns escaped/bounded text fallback metadata for a pet and input text.
- Include the pet's normalized `voice_profile` and state-derived mood context in the preview response when safe.
- Return explicit fields showing no audio was generated, no provider/network call was made, and the fallback cost is deterministic/transparent.
- Add docs entry for the endpoint if added.

## Scope

Allowed files:

- `mini_agent/tts.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Required Behavior

- Text fallback is always available locally when no TTS provider is configured.
- No audio bytes, audio URLs, recording, microphone, or provider payloads are generated or stored.
- Preview text must be bounded and reject secret-like content.
- Cost fields must be deterministic and visible. If fallback costs zero local compute food, say so explicitly and separately report the existing future voice action estimate where useful.
- Endpoint must be read-only: no food balance debit, no state mutation, no relationship memory mutation, no activity spam.
- Response must not echo raw secret-like text or unsupported provider names.
- HTTP errors should be bounded and stable.

## Non-Goals

- Do not implement real TTS, speech recognition, microphone access, audio playback, vendor adapters, PWA, desktop floating pet, 3D/VRM, billing, marketplace, account sync, or cloud sync.
- Do not debit compute food or create real audio.
- Do not add new Claude C/D worker files.
- Do not modify `evals/run_evals.py`; Claude B owns eval coverage.
- Do not claim real voice features are shipped.

## Safety Boundaries

- No voice cloning by default.
- No recording by default.
- No hidden background listening.
- No hidden network calls or provider execution.
- No purchase pressure, subscription pressure, hidden cost, or marketplace drift.
- No API keys, provider secrets, raw audio, speaker embeddings, real-person clone hints, or secret-like input in outputs.

## Verification

Run:

```bash
python3 -m unittest tests.test_http_server tests.test_webui_smoke
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes" mini_agent/tts.py mini_agent/http_server.py mini_agent/static/index.html tests/test_http_server.py tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-172A` and include:

- Summary of implementation changes
- Public contract changes
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
