# TASK-187A/187B Review — Extract Pet Room Voice Preview native module

**Status: APPROVED**

## Summary

TASK-187A extracts Pet Room voice preview into `voice-preview.js` as a native ES module. TASK-187B adds 6 evals and fixes existing speech/consent evals for combined surface scanning. Implementation correctly preserves consent-before-call, validation, auth delegation, meta rendering, and API boundary contract.

## Findings

### 1. voice-preview.js — Bounded Native ES Module ✅

- Single exported function: `wireVoicePreview(getCurrentPet, api, onAuthError)`
- Module docstring explicitly lists owned DOM elements and non-goals
- Uses `escapeHtml` for meta tag rendering
- No direct `fetch()`, no `PetAPI` literal, no `/pet/voice-preview` endpoint literal
- Does NOT mutate pet state, food, activity, or relationship memory

### 2. index.html — Minimal Boundary Wiring ✅

- Import: `import { wireVoicePreview } from '/static/components/voice-preview.js'`
- Inline handler replaced with: `wireVoicePreview(function(){ return currentPet; }, PetAPI, handleAuthError)`
- API delegation preserved: `api.previewVoice()` injected, not hardcoded
- Auth delegation preserved: `onAuthError` callback injected
- No `/pet/voice-preview` endpoint literal in index.html

### 3. Consent/Validation/Rendering Preserved ✅

- **Consent gate**: `consent.checked` validation before API call
- **Empty/over-500 validation**: Bounded error messages, no API call
- **Auth error delegation**: `onAuthError({status: 401})` on `_authError` rejection
- **Preview failure**: Error message displayed, bubble hidden
- **Text rendering**: `textContent` for bubble text (safe)
- **Meta rendering**: `innerHTML` with `escapeHtml()` for tags (cost, no-audio, no-network, no-recording, no-food-debit, provider_status, audio_requires_confirmation)

### 4. Tests — Strong Contract Coverage ✅

Tests updated to use `PetAPI.previewVoice` mock instead of `_fetchHandler`:
- `test_speech_preview_calls_endpoint`: Verifies `api.previewVoice` called with `pet_id` and `text`, bubble visible, textContent set
- `test_speech_preview_shows_meta_tags`: Verifies cost, no-audio, no-network, no-recording, no-food-debit, provider, audio_requires_confirmation tags
- `test_speech_preview_empty_shows_error`: Empty input → error, no API call
- `test_speech_preview_too_long_shows_error`: Over-500 input → error, no API call
- `test_voice_consent_unchecked_blocks_preview`: Unchecked consent → error, no API call

### 5. Evals — Combined Surface Scanning ✅

**6 new evals** (`voice_preview_module_*`):
- `voice_preview_module_file_present` — file exists, has ES exports, no build tooling
- `voice_preview_module_wired` — index.html references voice-preview with module import
- `voice_preview_module_markers_preserved` — all required markers present across HTML/JS
- `voice_preview_module_delegated_api_boundary` — uses `api.previewVoice` or `previewVoice` parameter, no direct fetch, no `/pet/voice-preview` literal
- `voice_preview_module_consent_validation_and_escaping` — consent gate, validation, textContent/escapeHtml
- `voice_preview_module_no_audio_or_scope_drift` — no external URLs, build system, audio/recording/marketplace/PWA/3D copy

**Existing evals fixed** — use `_read_voice_preview_surface()` helper to scan combined `index.html` + `voice-preview.js`:
- `eval_speech_bubble_markers_present`
- `eval_voice_preview_ui_cost_and_no_audio_copy`
- `eval_speech_bubble_escapes_preview_text`

All 9 required contract fields preserved: `cost_tokens`, `has_audio`, `no_network_call`, `no_recording`, `food_debit`, `provider_status`, `audio_requires_confirmation`, `cost` tag, `no-audio` tag.

### 6. No Scope Drift ✅

- ✅ No direct `fetch()` or `/pet/voice-preview` endpoint literal in module
- ✅ No real TTS/audio/recording/voice cloning
- ✅ No payment/marketplace
- ✅ No PWA/native
- ✅ No 3D/VRM
- ✅ No build system markers

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 421 tests OK
python3 evals/run_evals.py → 756 passed, 0 failed, 0 skipped
git diff --check → clean
```
