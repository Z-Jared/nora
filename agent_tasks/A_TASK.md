# TASK-173A: Pet Room speech bubble text fallback surface

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is in progress. Voice Profile v1 and TTS text fallback boundary are integrated. Phase 2 still uses A/B only; do not open or assume Claude C/D because current speech-bubble/presence work still shares Web UI, HTTP, tests, and eval files. Read first:

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
- `tests/test_webui_smoke.py`
- `tests/test_http_server.py`

## Goal

Add a visible Pet Room speech bubble surface that uses the existing text fallback voice-preview contract. The UI should let Nora show a safe text preview near the pet avatar with no real audio, no provider/network execution, no recording, no food debit, and transparent cost/no-audio metadata.

Suggested implementation shape:

- Add a speech bubble DOM area near the robot avatar in `mini_agent/static/index.html`.
- Add a small text input or preview button that calls `POST /pet/voice-preview` for the current pet.
- Render returned fallback text, `cost_tokens`, and no-audio/no-provider/no-recording metadata in bounded UI text.
- Escape all dynamic text. Do not use raw `innerHTML` for server/user-provided text.
- Handle missing/invalid/secret/over-limit input with bounded UI error copy.
- Keep the feature local/text-only; no audio controls or microphone controls.

## Scope

Allowed files:

- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `tests/test_http_server.py` only if a small HTTP contract assertion is needed
- `agent_tasks/A_DONE.md`

Do not modify:

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/tts.py` unless a tiny public-contract bug is discovered and documented
- payment/billing/provider/native desktop/PWA files

## Required Behavior

- Pet Room includes stable speech bubble markers/classes/ids suitable for tests/evals.
- Speech preview uses `/pet/voice-preview`; it must not call any real TTS/provider/audio/mic path.
- UI displays text fallback and cost/no-audio/no-network/no-recording metadata when preview succeeds.
- UI errors are bounded and do not echo raw secret-like text or over-limit text.
- Dynamic text is escaped through DOM text APIs or existing escape helpers.
- No activity event, relationship memory, food debit, or pet state mutation is introduced.

## Non-Goals

- Do not implement real TTS, audio playback, speech recognition, microphone access, vendor adapters, PWA, desktop floating pet, 3D/VRM, billing, marketplace, account sync, cloud sync, or Claude C/D worker setup.
- Do not add promotional voice cloning, recording by default, always/background listening, hidden costs, purchase pressure, or marketplace copy.

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|real payment|audio_url|audio bytes|microphone|mic access" mini_agent/static/index.html tests/test_webui_smoke.py tests/test_http_server.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-173A` and include:

- Summary of implementation changes
- Public UI contract/DOM markers added
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
