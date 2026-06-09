# TASK-181A: Extract Pet Room design tokens and CSS modules — DONE

## Summary

Extracted Pet Room design tokens and CSS into native static CSS files without changing behavior, DOM markers, API calls, or requiring a build step.

## Changes Made

### 1. `mini_agent/static/styles/tokens.css` (new)
- Defined stable CSS custom properties for all Pencil/Pet Room values:
  - Canvas: `--pet-canvas-max-w`, `--pet-canvas-fill` (#F5F3EE), `--pet-canvas-stroke` (#D8D1C8), `--pet-canvas-radius`, `--pet-canvas-shadow`
  - Wall/floor: `--pet-wall-fill` (#F1EEE7), `--pet-floor-fill` (#DDD5CA)
  - Ground shadow: `--pet-shadow-fill` (#B9AA993D)
  - Chip colors: `--pet-chip-mood` (#F6DDC6), `--pet-chip-presence` (#DDE6DC), `--pet-chip-energy` (#ECE3D6), `--pet-chip-bond` (#E8DED4)
  - Chip text colors: mood (#6C412B), presence (#385744), energy (#5B4D3F), bond (#654C3E)
  - Ceramic body: `--pet-ceramic-light`, `--pet-ceramic-dark`, `--pet-ceramic-border`, `--pet-ceramic-eye`, `--pet-ceramic-core-light/dark`
  - Action dock: `--pet-action-bg` (#EFE9E0), `--pet-action-primary-bg` (#8F5A3C), dock border (#D8D1C8)
  - Stat bars: hunger (#e8755a), energy (#5a9de8), mood (#e8b55a), bond (#b55ae8), growth (#5ae875), food (#4fc3f7)
  - Speech bubble: border (#b0bec5), gradient (#eceff1 → #cfd8dc)
  - Typography: `--pet-name-size` (40px), `--pet-role-size` (15px), chip label/value sizes
  - Referenced `NORA_PET_ROOM_FRONTEND_CONTRACT.md` in file comment

### 2. `mini_agent/static/styles/pet-room.css` (new)
- Moved all Pet Room CSS rules from `index.html` into this file
- Used variables from `tokens.css` for Pencil-derived values
- Preserved all selectors and DOM markers
- Includes: room shell, canvas, wall/floor, hero area, ceramic body, name/role, status chips, avatar, skill shelf, identity, stats, action dock, food section, cost table, mood summary, reaction/notice, greeting, today/diary, speech bubble, voice consent, activity/memory/editor, loading, responsive media query
- Also includes robot avatar CSS, expression state classes, presence state classes, and all animations

### 3. `mini_agent/static/index.html`
- Added `<link rel="stylesheet" href="/static/styles/tokens.css">` and `<link rel="stylesheet" href="/static/styles/pet-room.css">` in `<head>`
- Removed all Pet Room CSS from inline `<style>` block (lines 201-418)
- Preserved non-Pet Room UI CSS (topbar, sidebar, messages, composer, inspector, mobile layout, session/task/memory forms)
- No DOM IDs/classes/markers changed
- No JS behavior changed

### 4. `tests/test_webui_smoke.py`
- Added 3 new tests:
  - `test_stylesheet_links_exist` — verifies both `<link>` tags exist in index.html
  - `test_pet_room_css_contains_design_tokens` — verifies pet-room.css uses token variables
  - `test_tokens_css_defines_pencil_values` — verifies tokens.css has Pencil hex values (#F5F3EE, #F6DDC6, etc.)

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server
Ran 381 tests in 144.092s — OK

git diff --check
(no whitespace errors)

rg scan
1 hit: https://api.openai.com/v1 in index.html LLM setup guidance (pre-existing, not introduced)
```

## What Changed vs What Didn't

**Changed:**
- CSS moved from inline `<style>` to `styles/pet-room.css`
- Design constants defined as CSS variables in `styles/tokens.css`

**NOT changed:**
- DOM structure, IDs, classes, markers — all preserved
- JS behavior — all preserved
- API endpoints — none added or changed
- Build step — none required
- React/Vite/TypeScript/npm — not introduced
