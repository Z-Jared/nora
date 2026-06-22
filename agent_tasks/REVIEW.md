# Review Report: TASK-189A + TASK-189B

**Status: APPROVED**

## Summary

TASK-189A makes the Web UI initial viewport unmistakably pet-first. TASK-189B locks that contract with 6 deterministic evals. Both tasks are correctly scoped, well-tested, and free of scope drift.

## Findings

### 1. Behavior Correctness ✅

- `currentView` defaults to `'pet'` — correct.
- `.pet-room` CSS default changed to `display: block` — correct.
- `thread-head` and `messages-wrap` get `style="display:none"` — correct for initial state.
- `nav-pet` gets `active` class by default — correct.
- Startup calls `loadPet()` when `currentView === 'pet'` — correct and minimal.
- `switchView()` function properly handles both directions: pet→chat hides pet room and shows thread; chat→pet shows pet room and hides thread — no regression.

### 2. CSS/HTML Boundary ✅

- Inline styles are minimal and justified: `display:block`/`display:none` for initial viewport state.
- CSS rule change is a single property: `.pet-room { display: block }`.
- No unnecessary CSS classes or over-engineering.
- The approach is the smallest possible change to achieve the goal.

### 3. Test Coverage ✅

**Claude A smoke tests (3 new):**
- `test_pet_room_default_css_visible` — locks CSS default to `display:block`
- `test_pet_room_first_screen_markers` — locks 14 first-screen DOM markers + default view
- `test_startup_loads_pet_content_without_switchView` — locks startup `loadPet()` path with async wait

**Claude B evals (6 new):**
- `pet_first_screen_markers_present` — required markers exist in HTML/CSS
- `pet_first_screen_local_hero_image` — local-only Nora-01 asset
- `pet_first_screen_not_hidden` — no `display:none` on pet room root
- `pet_first_screen_modules_wired` — all 5 native modules imported
- `pet_first_screen_no_scope_drift` — no build-system or product scope drift
- `pet_first_screen_startup_loads_pet` — startup calls `loadPet()` with conditional check

**Mock fix:** `test_add_food_endpoint_normalizes_to_food_added` now returns valid pet shape (pre-existing fragility exposed by startup `loadPet()` call).

### 4. No Scope Drift ✅

Scope drift scan clean. All `rg` hits are:
- Existing `pet-room-reaction` CSS/HTML/JS (pre-existing)
- Eval negative assertions checking forbidden patterns (pre-existing)
- `setup_guidance` URL in `index.html` (pre-existing)

No new forbidden markers introduced:
- ❌ No React/Vite/TypeScript/npm/build system
- ❌ No real audio/TTS/recording/voice cloning
- ❌ No payment/billing/marketplace
- ❌ No PWA/native/desktop
- ❌ No 3D/VRM/Live2D

### 5. Backward Compatibility ✅

- Chat view still accessible via nav toggle
- `switchView('chat')` correctly shows thread-head, messages-wrap, composer
- All existing Pet Room module wiring preserved
- No endpoint changes, no API contract changes

### 6. Architecture Consistency ✅

- Changes align with Pet Agent MVP first-screen requirement
- Module boundaries (native ES modules) preserved
- API delegation through `PetAPI` preserved
- No new files outside allowed scope

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 438 tests OK
python3 evals/run_evals.py → 768 passed, 0 failed, 0 skipped
git diff --check → clean
```

## Verdict

**APPROVED** — Both tasks are correctly implemented, well-tested, and ready for integration.
