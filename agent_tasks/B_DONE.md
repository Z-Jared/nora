# B DONE — TASK-183B

**Status:** Complete — all pet_room_canvas evals PASS

## Summary

Added 5 deterministic evals for Pet Room Canvas module. All evals active/pass when combined with TASK-183A.

## Evals Added

1. **`pet_room_canvas_module_file_present`** — `pet-room-canvas.js` exists with native ES module exports, no build tooling.
2. **`pet_room_canvas_module_index_wired`** — `index.html` references `pet-room-canvas` with `<script type="module">`.
3. **`pet_room_canvas_markers_preserved`** — All required design markers present: `pet-room-design-shell`, `pet-room-canvas`, `pet-room-hero-image`, `pet-room-status-chip`, `pet-room-name`, `pet-room-role`, chip values, hero asset path.
4. **`pet_room_canvas_read_only_no_api_or_fetch`** — Canvas module has no `fetch(`, `petapi.`, `/pet/`, voice-preview, relationship-memory, or mutation calls in code (comments excluded).
5. **`pet_room_canvas_no_external_or_scope_drift`** — No external URLs, build system markers, or scope drift.

## Verification

### Own worktree (no TASK-183A)

```
python3 evals/run_evals.py           → 729 passed, 0 failed, 5 skipped
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 387 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-183A)

```
python3 evals/run_evals.py           → 5/5 pet_room_canvas evals PASS
```
