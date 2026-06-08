# TASK-174A/174B Review — Voice Consent and Cost Confirmation Boundary

**Status: APPROVED**

## Summary

TASK-174A adds consent checkbox and cost/provider metadata to the voice preview flow. TASK-174B adds 5 deterministic evals locking the consent boundary. All review criteria satisfied.

## Review Findings

### 1. Voice Preview Metadata — Text-Only, Read-Only

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Text-only, no real TTS | ✅ | `TextFallbackTTSAdapter.preview()` returns `has_audio: False`, `source: "text_fallback"` |
| No food debit | ✅ | `food_debit: False` in response metadata |
| No provider/network | ✅ | `provider_status: "not_configured_text_fallback"`, `no_network_call: True` |
| No recording | ✅ | `no_recording: True` |
| Requires confirmation | ✅ | `requires_user_confirmation: True`, `confirmation_kind: "text_fallback_voice_preview"` |
| Audio requires confirmation | ✅ | `audio_requires_confirmation: True` |

All 5 new metadata fields are safe booleans/strings. No raw data exposed.

### 2. Consent Checkbox Prevents Fetch

**HTML structure** (index.html):
- `voice-consent-panel` with boundary text, cost/provider meta, checkbox
- Checkbox label: "I understand this is a text-only preview with no real audio"

**JS guard** (speech-preview-btn onclick):
```javascript
var consent = document.getElementById('voice-consent-checkbox');
if(!consent.checked){
  errorEl.textContent = 'Please confirm the consent boundary first.';
  return;  // blocks fetch
}
```

- ✅ `voice-consent-checkbox` checked before fetch
- ✅ `.checked` property used (fail-closed)
- ✅ Return before fetch if unchecked
- ✅ Bounded error message with consent semantics

### 3. Dynamic Text Rendering Escaped

| Element | API | Status |
|---------|-----|--------|
| `speech-bubble-text` | `textContent` | ✅ |
| `speech-bubble-meta` | `innerHTML` + `escapeHtml` | ✅ |
| `speech-bubble-error` | `textContent` | ✅ |
| Consent boundary text | Static HTML | ✅ |

### 4. Eval Coverage Strength

| Eval | What it locks |
|------|---------------|
| `voice_consent_markers_present` | All 6 required markers: panel, checkbox, boundary, cost, provider, `/pet/voice-preview` |
| `voice_consent_unchecked_no_fetch` | Handler reads checkbox, checks `.checked`, has return before fetch, consent/confirm semantics |
| `voice_cost_confirmation_metadata` | Consent panel contains cost, text-only, no-network, no-recording, no-debit; JS uses food_debit, provider_status, audio_requires_confirmation |
| `voice_cost_confirmation_http_metadata` | `/pet/voice-preview` response includes all 8 required fields: requires_user_confirmation, confirmation_kind, audio_requires_confirmation, provider_status, food_debit, has_audio, no_network_call, no_recording, cost_tokens |
| `voice_consent_no_recording_or_marketplace_copy` | No voice clone/recording/background listening/marketplace/promotional copy |

Evals are substantive — they check DOM structure, JS control flow, HTTP response fields, and copy safety. Not just file-existence.

### 5. Scope Compliance

- ✅ No real TTS provider integration
- ✅ No audio playback, microphone, or recording
- ✅ No billing, marketplace, or payment
- ✅ No PWA, desktop, or 3D work
- ✅ No Claude C/D worker setup

### 6. B_DONE Report Note

Claude B's B_DONE says "4 evals" but the diff adds 5 (including `voice_cost_confirmation_http_metadata`). Code and PM verification (691 passed) are authoritative. Not blocking.

## Verification

- 284 unit tests OK
- 691 evals passed, 0 failed, 0 skipped
- git diff --check: clean
- Forbidden-copy scan: only negative safety assertions and tts.py docstrings
