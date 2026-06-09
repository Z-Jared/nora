# B DONE — TASK-182B

**Status:** Complete — API boundary drift fixed, combined check PASS

## Summary

Fixed 4 evals that broke when TASK-182A moved `/pet/voice-preview` endpoint from `index.html` to `api.js`. All evals now accept the new API boundary pattern.

## Fixes Applied

### `speech_bubble_markers_present`
- Removed `/pet/voice-preview` from required HTML markers
- Now checks `api.js` exists and contains the endpoint, OR `index.html` has it

### `speech_bubble_escapes_preview_text`
- Preview request check now searches both `index.html` + `api.js`
- Accepts `PetAPI.previewVoice(...)` or `preview_voice(...)` as valid API call pattern
- Still requires `pet_id` and `text` in the request

### `voice_consent_markers_present`
- Removed `/pet/voice-preview` from required HTML markers
- Now checks `api.js` for endpoint presence

### `voice_consent_unchecked_no_fetch`
- Consent guard check now looks for `fetch(`, `petapi`, `previewvoice`, or `preview_voice` as API call markers
- Still requires consent check (checkbox + `.checked` + `return`) before API call

## Verification

### Own worktree (no TASK-182A)

```
python3 evals/run_evals.py           → 724 passed, 0 failed, 5 skipped
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 381 tests OK
git diff --check                     → clean
```

### Combined check (applied onto TASK-182A)

```
python3 evals/run_evals.py           → 729 passed, 0 failed, 0 skipped
```
