# B DONE — TASK-187B

**Status:** Complete — PM-review fix applied, all evals PASS

## Summary

Fixed 2 evals that failed combined PM review with TASK-187A. Both now use `_read_voice_preview_surface()` to scan combined `index.html` + `voice-preview.js` surface.

## PM-Review Fix

### `eval_voice_preview_ui_cost_and_no_audio_copy`
- **Before:** Read only `index.html` — missed no-network/provider indicators in `voice-preview.js`
- **After:** Uses `_read_voice_preview_surface()` to scan combined surface

### `eval_voice_cost_confirmation_metadata`
- **Before:** Searched `index.html` for `speech-bubble-meta` JS rendering path — not found after extraction
- **After:** Consent panel HTML checks still from `index.html`; JS meta rendering path searched in combined surface

Both evals preserve original assertions (cost, no-audio, no-network, no-recording, food_debit, provider_status, audio_requires_confirmation).

## Evals Added (6)

1. `voice_preview_module_file_present`
2. `voice_preview_module_wired`
3. `voice_preview_module_markers_preserved`
4. `voice_preview_module_delegated_api_boundary`
5. `voice_preview_module_consent_validation_and_escaping`
6. `voice_preview_module_no_audio_or_scope_drift`

## Existing Evals Updated (6)

- `_read_voice_preview_surface()` helper for combined surface reading
- `eval_speech_bubble_markers_present`
- `eval_speech_bubble_escapes_preview_text`
- `eval_voice_consent_markers_present`
- `eval_voice_consent_unchecked_no_fetch`
- `eval_voice_preview_ui_cost_and_no_audio_copy` (PM fix)
- `eval_voice_cost_confirmation_metadata` (PM fix)

## Verification

### Own worktree (no TASK-187A)

```
python3 evals/run_evals.py           → 750 passed, 0 failed, 6 skipped
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 411 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-187A)

```
python3 evals/run_evals.py           → 756 passed, 0 failed, 0 skipped
All voice_preview + speech_bubble + voice_consent evals PASS
```
