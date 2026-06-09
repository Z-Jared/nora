# TASK-184A: Extract Pet Room Status Chips native module

## Summary

Created `mini_agent/static/components/status-chips.js` and moved Mood/Presence/Energy/Bond chip text updates out of `pet-room-canvas.js` into a smaller native ES module.

## Changes

### New file: `mini_agent/static/components/status-chips.js`
- Exports `updateStatusChips(state, expr, pres)` function
- Owns only: `chip-mood-value`, `chip-presence-value`, `chip-energy-value`, `chip-bond-value`
- Uses `textContent` only (no HTML insertion)
- Read-only: no fetch, no PetAPI, no external URLs

### Updated: `mini_agent/static/components/pet-room-canvas.js`
- Imports `updateStatusChips` from `status-chips.js`
- `updateCanvas()` delegates chip updates to `updateStatusChips()`
- `updateChips()` delegates to `updateStatusChips()`
- Still owns `pet-room-name` and `pet-room-role` text updates

### Updated: `tests/test_webui_smoke.py`
- Added `StatusChipsModuleTests` class with 7 tests:
  - Module exists as native ES module
  - Exports `updateStatusChips`
  - No fetch/PetAPI/URL references
  - Uses `textContent` not `innerHTML`
  - References all four chip value IDs
  - Canvas module delegates to status-chips
  - `renderPet` still updates chip values via delegation

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server
Ran 400 tests in 147.143s — OK

git diff --check
(clean)

rg scan
No hits in status-chips.js or pet-room-canvas.js
Only allowed PetAPI usage in index.html and existing fetch calls
```

## Non-Goals Preserved
- No new endpoints, React/Vite/TS, food/voice/memory extraction
- No real TTS, PWA, 3D/VRM, billing, marketplace
