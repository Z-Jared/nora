# TASK-182A: Extract Pet Room API boundary into native api.js — DONE

## Summary

Created `mini_agent/static/api.js` as a native ES module and wired it into `index.html` via `<script type="module">` with `import * as PetAPI`. All Pet Room fetch calls centralized behind exported functions. Endpoint shapes, auth, DOM markers, and UI behavior unchanged.

## Changes

### `mini_agent/static/api.js` (new — ES module)
- Native ES module with named `export` functions
- Exports: `getPetCurrent`, `getPetActivity`, `getPetFoodStatus`, `getRelationshipMemory`, `createPet`, `addPetFood`, `feedPet`, `carePet`, `updatePetIdentity`, `previewVoice`, `createRelationshipMemory`, `PET_ENDPOINTS`, `post`
- Auth: reads `#token` input, sets `Authorization: Bearer` header
- Same-origin only, no external URLs, no build step

### `mini_agent/static/index.html`
- `<script type="module">` with `import * as PetAPI from '/static/api.js'; window.PetAPI = PetAPI;`
- All Pet Room fetch calls replaced with `PetAPI.*` wrappers
- Auth error handling preserved via `_authError` catch pattern

### `tests/test_webui_smoke.py`
- `_extract_script()` updated to handle `<script type="module">` and strip import/assignment lines
- Mock `PetAPI` in harness updated (`post` instead of `_post`)
- New tests: `test_index_html_uses_module_import`, `test_api_js_has_exports`

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server
Ran 387 tests in 143.730s — OK

git diff — check
clean

rg forbidden scan
(no introduced forbidden copy)
```
