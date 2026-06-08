# TASK-172A/172B Review — TTS Adapter Protocol with Text Fallback

**Status: APPROVED**

## Summary

TASK-172A implements a read-only `/pet/voice-preview` endpoint with deterministic text fallback. TASK-172B adds 5 evals covering cost transparency, secret rejection, and read-only behavior. All review criteria satisfied.

## 1. Read-Only Behavior

| Criterion | Status | Evidence |
|-----------|--------|----------|
| No food debit | ✅ | Handler calls `adapter.preview()` only — no `feed_pet` or `add_food` calls |
| No state mutation | ✅ | Pet state read via `pet.state.to_dict()` but not modified |
| No activity events | ✅ | `eval_tts_preview_read_only_no_food_or_state_mutation` verifies activity count unchanged after 5 preview calls |
| No relationship memories | ✅ | Same eval verifies memory count unchanged |
| No pet creation side effects | ✅ | Handler only reads existing pet via `get_pet(pet_id)` |

## 2. Text Bounded at 500 Chars

- `VOICE_PREVIEW_TEXT_MAX_LEN = 500` constant in `tts.py:18`
- Handler checks `len(text) > VOICE_PREVIEW_TEXT_MAX_LEN` → 400 error
- Error response: `{"error": "text too long", "max_length": 500}` — does NOT echo raw text
- `test_voice_preview_rejects_text_too_long` verifies 501 chars → 400, no raw text in response
- `test_voice_preview_accepts_text_at_max_length` verifies 500 chars → 200

## 3. Secret Rejection

- `is_sensitive_text(text)` check on input text → 400 `{"error": "rejected sensitive text"}`
- `eval_tts_preview_rejects_secret_text` verifies:
  - Secret in text body → rejected, not echoed
  - Secret in voice_id field → rejected, not echoed
- Handler does not echo raw secret text in any error response

## 4. No Real TTS / No Provider / No Audio

| Criterion | Status | Evidence |
|-----------|--------|----------|
| No real TTS | ✅ | `TextFallbackTTSAdapter` always returns `audio_bytes=None` |
| No provider/network call | ✅ | Adapter is purely deterministic, no imports of real TTS providers |
| No audio bytes exposed | ✅ | `TTSResult.to_dict()` returns `has_audio: False`, never includes audio_bytes |
| No recording/microphone | ✅ | Response includes `"no_recording": True` |
| No audio URL | ✅ | No URL fields in response |

## 5. Cost Transparency

- `estimate_voice_cost()` deterministic: `len(text) // 10 * speed_multiplier`
- Speed multipliers: slow=1.2, normal=1.0, fast=0.8
- Preview response includes `cost_tokens`, `voice_profile`, `mood_context`, `no_audio_reason`, `no_network_call`, `no_recording`
- `eval_tts_preview_cost_transparent` verifies cost metadata present

## 6. Eval Quality (5 evals)

| Eval | What it verifies |
|------|-----------------|
| `tts_preview_cost_transparent` | Cost metadata present in response |
| `tts_preview_rejects_secret_text` | Secret text rejected, not echoed |
| `tts_preview_read_only_no_food_or_state_mutation` | Food balance, hunger, energy, mood, activity count, memory count all unchanged |
| (2 more) | Guard function and compatibility |

All evals use `_skip_if_no_tts()` guard — skip when TASK-172A absent, pass when present. Combined check: 5/5 PASS, 682 evals total, 274 unit tests OK.

## 7. Scope Compliance

- No real TTS provider integration (deferred to PHASE2-10)
- No voice cloning
- No recording/microphone access
- No food debit or state mutation
- No marketplace/billing language

## Verification

```
python3 -m unittest tests.test_http_server tests.test_webui_smoke → 274 tests OK
python3 evals/run_evals.py → 682 passed, 0 failed, 0 skipped
git diff --check → clean
rg forbidden phrases → only negative safety assertions and tts.py docstring
```
