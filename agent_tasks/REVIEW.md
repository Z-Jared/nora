# TASK-182A/182B Review — Extract Pet Room API boundary into native api.js

**Status: APPROVED**

## Summary

TASK-182A extracts Pet Room fetch calls into `api.js` as a native ES module. TASK-182B adds 5 evals and fixes existing speech/voice consent evals for endpoint migration. All review criteria satisfied.

## Findings

### 1. api.js Same-Origin/Auth/JSON/Error Compatibility

- **Same-origin only**: `api.js` uses `fetch()` with relative paths (`/pet/current`, `/pet/feed`, etc.). No external URLs.
- **Auth preserved**: `_authHeaders()` reads `#token` input, sets `Authorization: Bearer` header. `_checkAuth()` rejects 401 with `_authError` promise rejection.
- **JSON/error behavior**: All endpoints use `.then(_checkAuth).then(_json)` pattern. POST helper uses `JSON.stringify(body)`.
- **No build step**: Pure ES module, no imports from React/Vite/TypeScript/npm/Webpack/Rollup.

### 2. index.html Module Import Compatibility

- **Module syntax**: `<script type="module">` with `import * as PetAPI from '/static/api.js'` and `window.PetAPI = PetAPI` for IIFE access.
- **IIFE preserved**: The existing IIFE `(function(){...})()` wrapper is preserved inside the module script.
- **Test harness updated**: `_extract_script()` handles module syntax, strips import/assignment lines. Mock `PetAPI` object delegates to `fetch()` so `_fetchHandler` mock still works.
- **All PetAPI calls verified**: `test_pet_room_fetch_calls_use_pet_api` checks all 10 endpoints use PetAPI wrappers, no raw fetch to `/pet/*`.

### 3. Pet Room Behavior Preserved

| Behavior | Status | Evidence |
|----------|--------|----------|
| Auth 401 handling | ✅ | `_authError` catch pattern in all `.catch()` handlers |
| Voice consent no-fetch-before-confirmation | ✅ | `eval_voice_consent_unchecked_no_fetch` updated to check `PetAPI.previewVoice` or `fetch` |
| Activity/memory/identity/food/status refresh | ✅ | All `loadPetActivity`, `loadRelationshipMemories`, `loadCostEstimates`, `loadTodayDiary` use PetAPI |
| Speech bubble preview | ✅ | `eval_speech_bubble_escapes_preview_text` updated to check `previewVoice` or `/pet/voice-preview` |

### 4. Eval Coverage (5 new evals)

| Eval | What it locks |
|------|---------------|
| `api_boundary_file_present` | api.js exists, uses ES module exports, no build tooling, no window global IIFE |
| `pet_room_api_endpoints_preserved` | All 10 required endpoints present in api.js |
| `pet_room_api_auth_header_preserved` | Authorization/bearer header present, no console.log of tokens |
| `pet_room_api_index_module_wired` | index.html uses `<script type="module">` with `import` from local api.js |
| `api_boundary_no_external_or_build_drift` | No external URLs, no build system markers (React/Vite/TypeScript/npm/Webpack/Rollup) |

**Existing eval fixes**: `eval_speech_bubble_markers_present`, `eval_speech_bubble_escapes_preview_text`, `eval_voice_consent_markers_present`, `eval_voice_consent_unchecked_no_fetch` updated to check api.js for endpoint references.

### 5. No Scope Drift

- ✅ No React/Vite/TypeScript/npm/Webpack/Rollup
- ✅ No external URLs
- ✅ No PWA/native/3D/VRM
- ✅ No marketplace/payment
- ✅ No voice/audio/recording beyond existing preview
- ✅ Same-origin fetch only

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 387 tests OK
python3 evals/run_evals.py → 729 passed, 0 failed, 0 skipped
git diff --check → clean
rg forbidden scan → only pre-existing negative assertions
```
