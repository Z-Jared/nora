# TASK-187A: Extract Pet Room Voice Preview native module — Completion Report

## Summary

Created `mini_agent/static/components/voice-preview.js` and moved the Pet Room text-only voice preview UI wiring out of `index.html` into a bounded native ES module. Preserved consent-before-call behavior, request shape, metadata rendering, DOM markers, and read-only safety boundaries.

## Changes

### New: `mini_agent/static/components/voice-preview.js`
- Exports `wireVoicePreview(getPet, api, onAuthError)` — wires speech-preview-btn click handler
- Preserves consent-before-call gate (checkbox must be checked)
- Preserves validation: empty text, over-500 chars
- Preserves request body: `{pet_id, text}`
- Renders text via `textContent`, meta via `escapeHtml`
- Meta tags: cost, audio status, no network, no recording, no food debit, provider, audio confirmation
- Auth error delegation to `onAuthError`
- Generic failure copy: `Preview failed.`
- No direct `fetch(`, no `PetAPI`, no external URLs, no build markers

### Modified: `mini_agent/static/index.html`
- Added `import { wireVoicePreview } from '/static/components/voice-preview.js'`
- Replaced inline `speech-preview-btn` onclick handler with `wireVoicePreview(function(){ return currentPet; }, PetAPI, handleAuthError)`
- All DOM IDs/classes/markers preserved

### Modified: `tests/test_webui_smoke.py`
- Test harness defines real `wireVoicePreview` implementation (not a no-op)
- Existing speech preview tests rewritten to exercise the real public contract path:
  - Mock `PetAPI.previewVoice` (the injected API the script's handler uses)
  - Dispatch click events on `speech-preview-btn` (triggers the handler wired by index.html script)
  - Assert request body `{pet_id, text}`, consent-before-call, empty/overlong validation, metadata rendering
- `VoicePreviewModuleTests` class tests also use `PetAPI.previewVoice` mock + dispatchEvent pattern
- Removed all ad-hoc click handler registrations, `fetch('/pet/voice-preview')` calls, and comments like "Register handler directly" / "wireVoicePreview is no-op"
- Updated `test_pet_room_fetch_calls_use_pet_api` to check `wireVoicePreview(` instead of `PetAPI.previewVoice(`

## PM-Review Fix (TASK-187A)

Fixed weak tests that bypassed the real public contract by registering ad-hoc click handlers in test bodies and directly calling `fetch('/pet/voice-preview')`. Tests now properly exercise the full contract path:

- `wireVoicePreview(getPet, api, onAuthError)` is already wired by the extracted index.html script
- Tests mock `PetAPI.previewVoice` (the injected API) and dispatch click events on `speech-preview-btn`
- No duplicate handler registration (avoids race between script's handler and test's handler)
- All 7 `PetRoomSmokeTests` speech-preview tests and 5 `VoicePreviewModuleTests` behavior tests rewritten

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server — 421 tests OK
git diff --check — clean
```

## Non-Goals Preserved
- No real TTS, audio, recording, voice cloning
- No new endpoints, React/Vite/TS, build steps
- No food debit, payment, marketplace
- No microphone/camera/screen/location
