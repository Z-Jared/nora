# TASK-173A/173B Review — Speech Bubble Text Fallback Surface

**Status: APPROVED**

## Summary

TASK-173A adds a visible speech bubble to Pet Room that calls `/pet/voice-preview` for text-only fallback preview. TASK-173B adds 4 deterministic evals with PM-strengthened assertions. All review criteria satisfied.

## Review Findings

### 1. Text-Only, No Real TTS/Audio/Microphone/Network

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Calls only `/pet/voice-preview` | ✅ | JS fetch at line ~860: `fetch('/pet/voice-preview', {...})` |
| No TTS provider code | ✅ | Only imports from `mini_agent.tts.TextFallbackTTSAdapter` (text fallback) |
| No audio playback | ✅ | No AudioContext, media elements, or audio URL handling |
| No microphone | ✅ | No getUserMedia, MediaRecorder, or mic access |
| No food debit | ✅ | Preview endpoint is read-only (verified in TASK-172A review) |
| No activity/memory mutation | ✅ | Endpoint only reads pet state, no write calls |

### 2. Safe DOM Text APIs

| Element | API Used | Status |
|---------|----------|--------|
| `speech-bubble-text` | `textContent` | ✅ Line ~870: `textEl.textContent = result.text \|\| ''` |
| `speech-bubble-meta` | `innerHTML` + `escapeHtml` | ✅ Line ~878: `escapeHtml(t)` for each tag |
| `speech-bubble-error` | `textContent` | ✅ Line ~868: `errorEl.textContent = result.error` |

`eval_speech_bubble_escapes_preview_text` locks this with regex-based fail-closed assertions.

### 3. Bounded Errors, No Secret/Over-Limit Echo

| Error Case | Response | Echoes Raw? |
|------------|----------|-------------|
| Empty text | `"Enter text to preview."` | No ✅ |
| Over 500 chars | `"Text too long (max 500)."` | No ✅ |
| API error | `result.error` (server-side bounded) | No ✅ |
| Catch/unknown | `"Preview failed."` | No ✅ |

Input is checked client-side (`text.length > 500`) and server-side (`VOICE_PREVIEW_TEXT_MAX_LEN`). Both reject without echoing.

### 4. Eval Coverage Strength

| Eval | What it locks |
|------|---------------|
| `speech_bubble_markers_present` | All 8 required DOM markers: area, bubble, text, meta, input, btn, error, `/pet/voice-preview` |
| `voice_preview_ui_cost_and_no_audio_copy` | All 4 metadata categories: cost indicator, no-audio/text-only, no-network/provider, no-recording |
| `speech_bubble_escapes_preview_text` | Fail-closed: textContent for text, escapeHtml for meta innerHTML, pet_id+text in request |
| `speech_bubble_no_recording_or_marketplace_copy` | No voice clone/recording/background listening/marketplace/promotional copy |

All evals use `_skip_if_no_speech_bubble()` guard — skip when TASK-173A absent, pass when present. PM strengthened all assertions from soft checks to fail-closed requirements.

### 5. Scope Compliance

- ✅ No PWA, desktop, 3D, billing, marketplace, or voice provider code
- ✅ Only adds speech bubble UI and 4 eval cases
- ✅ Uses existing `/pet/voice-preview` endpoint (TASK-172A)
- ✅ Forbidden scan: only negative safety assertions in evals

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 281 tests OK
python3 evals/run_evals.py → 686 passed, 0 failed, 0 skipped
git diff --check → clean
rg forbidden phrases → only negative safety assertions
```
