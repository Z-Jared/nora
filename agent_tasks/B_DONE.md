# B DONE — TASK-177B

**Status:** Complete — all room_greeting evals PASS

## Summary

Added 4 deterministic evals for room-load greeting. All evals active/pass when combined with TASK-177A.

## Evals Added

1. **`pet_room_greeting_markers_present`** — Pet Room exposes all required greeting DOM markers: `pet-room-greeting`, `pet-room-greeting-text`, `pet-room-greeting-meta`, `data-greeting`.
2. **`room_greeting_state_time_mapping_rules`** — Greeting mapping function references state fields (mood/energy/hunger/bond), time bucket (hour/morning/afternoon/evening), has fallback for missing/malformed state, and guards malformed date/time.
3. **`room_greeting_read_only_no_fetch`** — All greeting functions are CSS/DOM-only: no fetch, food_debit, /pet/, voice-preview, consent, microphone, camera, service-worker, notification, or register patterns.
4. **`room_greeting_no_voice_native_pwa_or_surveillance_copy`** — No voice cloning, recording, microphone/camera/screen/location access, marketplace, 3D/VRM, service worker, notification, or PWA install copy.

## Guard

Guard checks for `room-greeting`, `pet-greeting`, or `greeting` markers in `index.html`.

## Verification

### Own worktree (no TASK-177A)

```
python3 evals/run_evals.py           → 4/4 room_greeting evals SKIP
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 317 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-177A)

```
python3 evals/run_evals.py           → 4/4 room_greeting evals PASS
```

### `rg` scan

All hits are negative safety assertions. No promotional or enabling language.
