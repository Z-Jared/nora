# B DONE — TASK-181B

**Status:** Complete — all design_tokens/pet_room_css evals PASS

## Summary

Added 5 deterministic evals for design token extraction and CSS module wiring. All evals active/pass when combined with TASK-181A. Also fixed TASK-180B `pet_room_design_tokens_match_pencil` eval to check CSS files after extraction, and fixed `pet_room_css_no_build_or_scope_drift` to use word-boundary regex for `react` (avoids false positive on `reaction`).

## Evals Added

1. **`design_tokens_files_present`** — `tokens.css` exists with Pencil colors (`#F5F3EE`, `#D8D1C8`, `#F1EEE7`, `#DDD5CA`, `#F6DDC6`, `#DDE6DC`, `#ECE3D6`, `#E8DED4`) and CSS variables.
2. **`design_tokens_match_pencil_contract`** — tokens.css has radius and warm action color tokens.
3. **`pet_room_css_module_wired`** — `index.html` links both `/static/styles/tokens.css` and `/static/styles/pet-room.css` with local paths.
4. **`pet_room_css_preserves_markers`** — `pet-room.css` owns required selectors: `.pet-room-design-shell`, `.pet-room-canvas`, `.pet-room-hero-image`, `.pet-room-status-chip`, `.pet-actions`.
5. **`pet_room_css_no_build_or_scope_drift`** — No build system (`react`, `vite`, `typescript`, `npm install`, `webpack`, `rollup` as standalone words) or scope drift markers.

## Fixes to Existing Evals

- `pet_room_design_tokens_match_pencil` — Now checks HTML + CSS files (tokens were moved from HTML to CSS by TASK-181A)
- `pet_room_css_no_build_or_scope_drift` — Uses `\breact\b` word-boundary regex instead of substring match (avoids false positive on `reaction` CSS classes)

## Verification

### Own worktree (no TASK-181A)

```
python3 evals/run_evals.py           → 719 passed, 0 failed, 5 skipped
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 378 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-181A)

```
python3 evals/run_evals.py           → 9/9 design_tokens + pet_room_css evals PASS
```

### `rg` scan

All hits are negative safety assertions. No promotional or enabling language.
